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

## Execute DeepNext in GitLab / GitHub:

DeepNext is triggered by the following labels:

### State labels:
- `deep_next`:
    Indicates that DeepNext should read the issue and sprint to generating a merge request containing a solution to the issue without asking the user for help.
####
- `deep_next_human_in_the_loop`:
    Indicates that DeepNext should read the issue and propose an action plan in the issue's comments section for the user to accept. The user can then propose fixes to the action plan or accept it.

### Status labels:
- `deep_next_in_progress`:
    Indicates that DeepNext is currently working on the issue.
    ####
    This label is automatically added when DeepNext starts working on the issue and removed when DeepNext succeeds or fails at any point.
####
- `deep_next_solved`:
    Indicates that DeepNext has fully completed the issue (that is, published a merge request).
####
- `deep_next_failed`:
    Indicates that DeepNext has failed to complete the issue.
