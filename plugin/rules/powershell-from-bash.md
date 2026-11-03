## 调 PowerShell：`-Command` 整段用单引号

**在 Git Bash 里调用 PowerShell，`-Command` 后面那一整段一律用单引号包住，不要用双引号。**

双引号里 Bash 会先展开一遍，`$_`、`$?`、`$args`、`$env:TEMP` 到不了 PowerShell 手里：
`$_` 变成上一条命令的最后一个参数（没有时是空串），`$?` 变成上一条命令的退出码，
`$env:TEMP` 只剩 `:TEMP`；反引号还会被当成命令替换，PowerShell 的转义写法直接失效。
这几种都不报错——PowerShell 拿到的是被改过的命令，照常跑完，结果不对却看不出错在哪一步。

要把 Bash 的变量带进去，就在单引号外面拼接：`powershell -Command 'Write-Output '"$path"`。
单引号包住的这段里不能再出现单引号；确实要写，就断开成 `'"'"'`，或者把脚本存成 `.ps1`、改用
`-File` 调用——那条路不受这条规则影响，参数照常交给 Bash 展开。
