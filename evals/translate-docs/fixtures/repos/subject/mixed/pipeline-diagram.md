# Pipeline Diagram

The diagram below shows how a request flows through the pipeline.

```mermaid
graph TD
  A[User request] --> B{Router}
  B -->|fast| C[Fast path]
  B -->|safe| D[Safe path]
  C --> E[Result]
  D --> E
```

The same flow in Graphviz:

```dot
digraph pipeline {
  request -> router;
  router -> fast_path;
  router -> safe_path;
}
```

Run the loader with `pipeline-cli load --file config/widget.yaml` before starting.

| Command | Purpose |
|:---|:---|
| `pipeline-cli load` | Load a configuration file |
| `pipeline-cli run` | Start the pipeline |

See the log in var/log/pipeline.log when a step fails.
