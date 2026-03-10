module.exports = {
  apps: [
    {
      name: "lumiabot",
      script: "main.py",
      interpreter: "python3",
      cwd: "/docker/lumia-bot",
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000,
    },
  ],
};
