"""Upload the merged Glimmer checkpoint (about 60 GB) to Hugging Face straight from the Modal volume.

    .venv/bin/modal run engine/distill/publish_modal.py

A separate app from glimmer_modal.py, so the other jobs do not need the `huggingface` secret.
The model card comes from engine/distill/publish.py.
"""

import modal

WEIGHTS = "/weights"

app = modal.App("rehearsal-glimmer-publish")
weights = modal.Volume.from_name("glimmer-weights")
image = modal.Image.debian_slim(python_version="3.12").pip_install("huggingface_hub[hf_xet]")


@app.function(image=image, volumes={WEIGHTS: weights}, secrets=[modal.Secret.from_name("huggingface")],
              timeout=3 * 3600, cpu=4)
def upload(repo: str, card: str, run: str = "r1"):
    from huggingface_hub import CommitOperationAdd, HfApi
    api = HfApi()
    api.create_repo(repo, exist_ok=True)
    api.upload_folder(repo_id=repo, folder_path=f"{WEIGHTS}/glimmer_{run}",
                      commit_message=f"Rehearsal Glimmer {run}: merged bf16 checkpoint")
    api.create_commit(repo, [CommitOperationAdd("README.md", card.encode()),
                             CommitOperationAdd("LICENSE", f"{WEIGHTS}/glimmer/LICENSE")],
                      commit_message="Model card and license")
    print(f"https://huggingface.co/{repo}")


@app.local_entrypoint()
def main(run: str = "r1"):
    from huggingface_hub import HfApi
    from engine.check_api import load_env
    from engine.distill.publish import card, repos
    user = HfApi(token=load_env()["HF_TOKEN"]).whoami()["name"]
    upload.remote(repos(user)["merged"], card("merged", user), run)
