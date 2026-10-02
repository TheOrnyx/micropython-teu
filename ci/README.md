# CI - Docker stuff

This folder contains the dockerfile for the container containing all our pipeline dependencies,
along with a MicroPython build and our testing dependencies.

Uses the `tools/install_mpy_mip_deps.py` script in the container build to install any mip dependencies we'll need for testing.

## Build steps

Building the container should be done from the project root and here's how to build and push to container registry with podman:

First login with podman

```bash
podman login gitlab.ecs.vuw.ac.nz:45678
```

<details>
<summary>Old outdated build details from when it was building from private mirror repo</summary>

Since the container clones a private gitlab repo it needs an ssh key to do so.<br>
So make sure you have your ssh-agent active and that a key with access to the gitlab repo has been added.

```bash
# Start ssh agent - bash
eval $(ssh-agent -s)

# Start ssh agent - fish
eval (ssh-agent -c)

# Add your gitlab registered ssh key
ssh-add ~/.ssh/<key-filename>
```

Then build the container with the proper tag you want and pass in the ssh agent.

```bash
# Ran from project root
# Replace the part after the colon with the tag you want
podman build -t gitlab.ecs.vuw.ac.nz:45678/course-work/project489/2026/project/silouzaki/micropython-esp32-unix:mp_v1.29.0-with-stubs -f ./ci/Dockerfile --ssh default .
```

</details>

Then build the container with the proper tag you want from the repo root.

```bash
# Ran from project root
# Replace the part after the colon with the tag you want
podman build -t gitlab.ecs.vuw.ac.nz:45678/course-work/project489/2026/project/silouzaki/micropython-esp32-unix:mp_v1.29.0-with-stubs -f ./ci/Dockerfile .
```

You can quickly run the container if you want to test everything is working

```bash
podman run -it gitlab.ecs.vuw.ac.nz:45678/course-work/project489/2026/project/silouzaki/micropython-esp32-unix:mp_v1.29.0-with-stubs
```

Now push to the container registry whenever ready

```bash
podman push gitlab.ecs.vuw.ac.nz:45678/course-work/project489/2026/project/silouzaki/micropython-esp32-unix:mp_v1.29.0-with-stubs
```
