# Project Details

## Goal
Monitor Cinema City for "Avatar: Fire and Ashes" (IMAX 3D) and notify via Telegram.

## Configuration
- **Cinema URL**: https://www.cinemacity.cz/
- **Movie**: Avatar: Fire and Ashes
- **Format**: IMAX 3D
- **User Account**: (Credentials stored securely)

## Architecture
- **Monitor**: Uses Playwright to scrape the website.
- **Notifier**: Uses Telegram Bot API to send alerts.
- **Scheduler**: Runs the check periodically.
