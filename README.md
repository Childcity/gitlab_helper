# GitLab Helper

This repository contains Python scripts designed to assist with various GitLab-related tasks.

## Scripts

### `mr_build_watcher`
The `mr_build_watcher` script monitors the status of merge request (MR) pipelines in GitLab. It helps ensure that all pipelines are successfully completed before merging, providing real-time updates and notifications for any failures or issues.

Example:  
```bash
bash -c "cd /c/Dev/Examples/PythonScripts/gitlab_helper/ && source .venv/Scripts/activate && python src/mr_build_watcher.py --private-token=glpat-****** --state-file=src/comment_watcher_state.json --check-interval=600"
```

## Requirements
- Python 3.x
- Required dependencies (install via `pip install -r requirements.txt`)

## License
This project is licensed under the MIT License.