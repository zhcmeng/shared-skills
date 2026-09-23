# 通知渲染层：弹一条通知、撤掉某条通知，外加回答一个问题（你现在看的是不是这个会话）。
# 判定逻辑一概不在这里，在 plugin/hooks/notify 里（那一半纯逻辑、checks/verify.sh 能测；这一半只能肉眼验）。
#
# 为什么必须是 Windows PowerShell 5.1 而不是 7：这套系统通知接口属于 WinRT，PowerShell 7
# 加载不出来（本机实测报 "Unable to find type ToastNotificationManager"），只有系统自带的
# 5.1 能调。所以 hooks/notify 里是写死调 powershell.exe 的。
#
# 为什么通知的正文走命令行参数而不是文件：中文经 Git Bash 传给 5.1 不会乱码（本机按字符
# 码点实测过，参数和 UTF-8 文件两条路都对）。之前看着像乱码，那是 PowerShell 往管道写
# 输出的编码问题，不是入参问题。
param(
    [Parameter(Mandatory = $true)][ValidateSet('toast', 'clear', 'focused', 'match')][string]$Mode,
    [string]$Tag = '',
    [string]$Title = '',
    [string]$Body = '',
    [string]$Name = '',
    # 只给 match 那一档用：拿它当窗口标题来比，不真去读窗口。校验脚本靠这个口子单独验
    # 比对规则（真窗口在测试里摆不出来）
    [string]$WindowTitle = '',
    [switch]$DryRun
)

# 应用标识：不登记的话，通知署名会显示成「Windows PowerShell」。登记一次就够，系统之后
# 就认这个名字。写在 HKCU 下，不需要管理员权限，也不动系统里的任何东西。
$Aumid = 'ClaudeCode.Notify'
# 分组名配合标签用：同一个标签的通知会互相顶替，而不是堆成一串
$Group = 'claude-code'

function Initialize-AppId {
    $key = "HKCU:\SOFTWARE\Classes\AppUserModelId\$Aumid"
    if (Test-Path $key) { return }
    New-Item -Path $key -Force | Out-Null
    New-ItemProperty -Path $key -Name 'DisplayName' -Value 'Claude Code' -PropertyType String -Force | Out-Null
}

function New-ToastXml {
    param([string]$Title, [string]$Body, [bool]$Reminder)
    # 通知必须带一个可点的按钮，否则留不住。光写 scenario="reminder" 系统会静默忽略它：
    # 通知 25 秒后照样自己消失（那个 25 秒正是 duration="long" 的时长），而且不报错——
    # 所以下面那个「系统不接受就退成长时间显示」的兜底也永远不会触发。本机实测：同样
    # 条件下带按钮的通知挂了 100 秒仍在屏幕上，不带按钮的 25 秒就没了。
    # 常驻那一档的语义本来就是「你处理它才走」，按钮就是这个「处理」。
    # 按钮用系统内置的 dismiss，点了就是把这条通知关掉，不需要我们再做什么。
    # 标题和正文里的 & < > 会被 XML 解析器当成标签，必须转义
    $lines = "<text>$([System.Security.SecurityElement]::Escape($Title))</text>"
    if ($Body -ne '') {
        $lines += "`n      <text>$([System.Security.SecurityElement]::Escape($Body))</text>"
    }
    # duration 用 long：即便常驻那一档不被系统接受，也能多留一会儿
    $attrs = 'duration="long"'
    if ($Reminder) { $attrs = 'scenario="reminder" ' + $attrs }
    @"
<toast $attrs>
  <visual>
    <binding template="ToastGeneric">
      $lines
    </binding>
  </visual>
  <actions>
    <action content="知道了" arguments="dismiss" activationType="system" />
  </actions>
  <audio src="ms-winsoundevent:Notification.Reminder" />
</toast>
"@
}

function New-Notifier {
    [void][Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
    [void][Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime]
    [void][Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime]
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($Aumid)
}

function Show-Toast {
    param([string]$Title, [string]$Body)
    $notifier = New-Notifier
    # 常驻那一档先试。系统不接受就退成长时间显示，自己消失总好过什么都不弹。
    foreach ($reminder in @($true, $false)) {
        try {
            $xml = New-ToastXml -Title $Title -Body $Body -Reminder $reminder
            $doc = New-Object Windows.Data.Xml.Dom.XmlDocument
            $doc.LoadXml($xml)
            $toast = New-Object Windows.UI.Notifications.ToastNotification $doc
            # 标签 + 分组决定「同一个会话的新通知顶掉旧的」，而不是越堆越多
            $toast.Tag = $Tag
            $toast.Group = $Group
            $notifier.Show($toast)
            return
        } catch {
            if (-not $reminder) { throw }
        }
    }
}

function Remove-Toast {
    [void][Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
    [Windows.UI.Notifications.ToastNotificationManager]::History.Remove($Tag, $Group, $Aumid)
}


# 前台窗口上写着什么。读不到（拿不到前台窗口句柄）就回空 —— 「空」是「不知道」，不是
# 「不是」，这两件事在 hooks/notify 里走的是不同的路。
function Get-ForegroundTitle {
    Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public class ClaudeNotifyFg {
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
}
"@
    $h = [ClaudeNotifyFg]::GetForegroundWindow()
    if ($h -eq [IntPtr]::Zero) { return '' }
    $sb = New-Object System.Text.StringBuilder 1024
    [void][ClaudeNotifyFg]::GetWindowText($h, $sb, 1024)
    return $sb.ToString()
}

# 标题跟会话名算不算对得上，回三种答案之一：
#   'yes'  对上了 —— 你在看它
#   'no'   标题读到了，但名字不在里面 —— 你没在看它
#   ''     没得比（名字是空的，或者标题是空的）—— 不知道
# 「不知道」必须跟「不是」分开：前者要退回另一套判据（标记文件），后者可以直接定案。
#
# 对上的条件是：标题就是这个名字（有个开关能让标题不带图标），或者标题的第 2 位起正好是
# 这个名字。为什么卡在第 2 位：CLI 写进窗口标题的是 `${状态图标} ${会话名}`（2.1.274 的
# 拼装代码如此）—— 第 0 位图标、第 1 位空格、第 2 位起才是名字。图标会变（干活时在 ◐ ◑
# 之间转、空闲是 ✳），所以不能整条相等；名字后面什么都没有，所以也不能只要求开头对得上。
#
# 更不能放宽成「以空格 + 名字结尾」：会话名自己就带空格（本机在跑的就有「插件的 evals
# 设置」），那样比的话，名字「设置」会拿人家名字内部那个空格当分隔符，把别人的提醒压掉。
# 这里最初就是那么写的，被拿真窗口试的时候抓了出来（合成用例的名字都没空格，没盖住），
# 所以改成卡死位置。图标都是单字符（◐ ◑ ✳），固定切 2 位；将来若换成要两个码元的图标，
# 这里会判成「对不上」—— 方向是安全的那边（多弹一次，而不是把该弹的压掉）。
#
# 比的是码点（Ordinal），不走区域设置 —— 后者会忽略某些不可见字符，那正是撞名的温床。
function Get-TitleVerdict {
    param([string]$Title, [string]$Name)
    if ($Title -eq '' -or $Name -eq '') { return '' }
    if ($Title.Equals($Name, [StringComparison]::Ordinal)) { return 'yes' }
    if ($Title.Length -ge 2 -and $Title[1] -eq ' ' -and $Title.Substring(2).Equals($Name, [StringComparison]::Ordinal)) { return 'yes' }
    return 'no'
}

try {
    if ($Mode -eq 'match') {
        # 只比一对字符串，不碰窗口。给校验脚本留的口子：真窗口在测试里摆不出来，而上面
        # 那条比对规则是这一层唯一有判断的地方，值得能单独验
        Write-Output (Get-TitleVerdict -Title $WindowTitle -Name $Name)
        exit 0
    }

    if ($Mode -eq 'focused') {
        # 只回 yes / no / 空三个答案，都是 ASCII。中文经管道回给 bash 会乱码（入参方向
        # 不会，出参方向会，本机实测过），所以别让标题本身过管道
        Write-Output (Get-TitleVerdict -Title (Get-ForegroundTitle) -Name $Name)
        exit 0
    }

    if ($Mode -eq 'clear') {
        if ($DryRun) { Write-Output "clear $Tag"; exit 0 }
        Remove-Toast
        exit 0
    }

    if ($DryRun) {
        # 校验脚本要读这段 XML。PowerShell 默认按控制台的编码往管道写，中文会乱码，
        # 所以先掰成 UTF-8 再输出。
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
        Write-Output (New-ToastXml -Title $Title -Body $Body -Reminder $true)
        exit 0
    }

    Initialize-AppId
    Show-Toast -Title $Title -Body $Body
} catch {
    # 静默：通知弹不出来是小事，让 hook 报错是大事
}
exit 0
