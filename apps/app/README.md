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
- `deep_next_e2e`:  
    Indicates that DeepNext should read the issue and sprint to generating a merge request containing a solution to the issue without asking the user for help.
####
- `deep_next_propose_action_plan`:  
    Indicates that DeepNext should read the issue and propose an action plan in the issue's comments section for the user to accept. After proposing the action plan, a label `deep_next_awaiting_reaction` is added to the issue.  
    ####
    After the action plan is accepted, DeepNext will change the label to `deep_next_implement_action_plan` and perform the action related to this label.
####
- `deep_next_implement_action_plan`:  
    Indicates that DeepNext should read the issue and the accepted action plan from its comments section and implement a solution to the issue based on the action plan. The implementation results in creating a new merge request.
####

### Status labels:
- `deep_next_in_progress`:  
    Indicates that DeepNext is currently working on the issue.  
    ####
    This label is automatically added when DeepNext starts working on the issue and removed when DeepNext succeeds or fails at any point.
####
- `deep_next_awaiting_reaction`:  
    Indicates that DeepNext is waiting for the user to react (e.g. to the action plan that has been proposed by DeepNext).
####
- `deep_next_solved`:  
    Indicates that DeepNext has fully completed the issue (that is, published a merge request).
####
- `deep_next_failed`:  
    Indicates that DeepNext has failed to complete the issue.