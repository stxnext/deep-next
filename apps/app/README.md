# DeepNext App

DeepNext App is a Python application that uses the GitLab api and git repository to leverage
DeepNext core pipeline in production.

Steps:
1. Find issues dedicated for DeepNext to solve from registered projects
2. Prepare local git repo (with new feature branch)
3. Run DeepNext core pipeline
4. Create MR with the solution

---

# Run the app

> ⚠️ Required environment variables (use `.env` monorepo file):
>
>	```bash
>	# [...]
>
>	# APP
>	GITLAB_ACCESS_TOKEN="glpat-...-MxM2JY"
>	AWS_ACCESS_KEY_ID="AK...YHY"
>	AWS_SECRET_ACCESS_KEY="PQjzev...8RoZ"
>	AWS_DEFAULT_REGION="eu-central-1"
>	AWS_OUTPUT=json
>	```

## Run the app with Docker 🐳

### 1. Run Container

```bash
# From monorepo root directory
make app_docker_run
```
