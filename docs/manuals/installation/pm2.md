---
title: "PM2 (Process Manager)"
tags: [pm2, process-manager, node]
---

# :simple-pm2: Install PM2 (Process Manager 2)

**PM2** is a process manager tool based on Node.js, designed to manage and keep applications running in the background. It is particularly useful for Node.js applications but can also be used with other types of applications. PM2 provides features such as process monitoring, log management, and automatic restarts on failure or code changes.

## Official pages

- PM2: <https://pm2.keymetrics.io>
- Quick start guide: <https://pm2.keymetrics.io/docs/usage/quick-start>
- Single page guide: <https://pm2.keymetrics.io/docs/usage/pm2-doc-single-page>
- PM2 npm: <https://www.npmjs.com/package/pm2>
- PM2 logrotate: <https://www.npmjs.com/package/pm2-logrotate>

---

## Getting started

### Prerequisites

- Install **Node.js**
    - [RECOMMENDED] **[NVM](./nvm.md)**

### Installation

```sh
# Install PM2 through NPM:
npm install -g pm2

# Install pm2-logrotate to rotate logs for PM2:
pm2 install pm2-logrotate

# Check PM2 is running:
pm2 ping

# Check PM2 version:
pm2 -v
```

👍 ✨

INSTALLATION COMPLETE

---

## Usage

```sh
### Run application:

## Start node.js application in the background:
pm2 start app.js

## Start shell script app with naming "script-app":
pm2 start script.sh -n script-app

## Start the python application and watch for changes:
pm2 start python-app.py --watch

## Start binary file with arguments (--port 8080):
pm2 start binary-file -- --port 8080

## Use ecosystem configuration file:
# Generate a simple ecosystem.config.js file:
pm2 init simple
# Update the ecosystem.config.js file according to your needs:
nano ecosystem.config.js
# Start ecosystem.config.js:
pm2 start ecosystem.config.js

## Or use JSON file and start in the foreground:
pm2 start pm2-process.json --no-daemon

## Or use YAML file and specify log file path:
pm2 start pm2-process.yml --log /path/to/logs


### Check logs:
pm2 logs app-name --lines 50


### Restart application:
pm2 restart app-name


### Shows a list of applications registered into PM2:
pm2 list


### Monitor applications:
pm2 monit


### Stop and delete the application:
pm2 stop app-name
## Remove logs of the application:
pm2 flush app-name
## Delete the application:
pm2 del app-name


### Generate ecosystem.config.js file:
pm2 ecosystem


## Startup application on system reboot:
pm2 startup
#--------------------------------------------------------------------------------
## Run according to shown command!
# For example:
# [PM2] You have to run this command as root. Execute the following command:
#      $ sudo su -c "env PATH=$PATH:/home/user/.nvm/versions/node/v12.20.1/bin pm2 startup <distribution> -u <user> --hp <home-path>"
#--------------------------------------------------------------------------------
pm2 save


### Help:
pm2 --help
```

## References

- Ecosystem file: <https://pm2.keymetrics.io/docs/usage/application-declaration>
- Startup script: <https://pm2.keymetrics.io/docs/usage/startup>
- Logs: <https://pm2.keymetrics.io/docs/usage/log-management>
- Monitoring: <https://pm2.keymetrics.io/docs/usage/monitoring>
- Custom metrics: <https://pm2.keymetrics.io/docs/usage/process-metrics>
- Cluster mode: <https://pm2.keymetrics.io/docs/usage/cluster-mode>
- PM2 plus overview: <https://pm2.io/docs/plus/overview>
