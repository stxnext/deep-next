The DeepNext app relies on connecting to specified GitHub and/or Gitlab repositories.

For each repository, the DeepNext app scans the issues looking for specific labels that indicate DeepNext should take care of the issue.

DeepNext is triggered by the following labels:

## State labels:
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

## Status labels:
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
