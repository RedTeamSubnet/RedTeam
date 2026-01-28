---
title: Troubleshooting
tags:
    - troubleshooting
---

# Troubleshooting

## Docker permission problem

```sh
sudo usermod -aG docker ${USER}

# Init new group session without logout/login:
newgrp docker
# Or logout and login again:
gnome-session-quit --logout --no-prompt
# Or restart the server to apply changes:
sudo shutdown -r now
```
