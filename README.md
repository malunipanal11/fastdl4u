# Telegram MEGA Storage Bot

A Telegram bot that integrates with MEGA.nz to store, share, and retrieve files with secret code functionality and expiration logic.

## 📦 Features

- Admin-only /add to upload files with auto-generated 24-hour codes.
- Users can request files via secret codes.
- Admin can approve/deny access.
- Auto-upload to MEGA in `Telegram Storage/` with media categorization.
- Public commands like `/images`, `/videos`, `/audio` for random media previews.
- Commands restricted by user role (admin/user).
- Temporary welcome image with age disclaimer.
- Inline buttons for play/download/request on file listings.

## ⚙️ Setup

### 1. Clone & Install

```bash
git clone https://github.com/yourname/telegram-mega-bot.git
cd telegram-mega-bot
pip install -r requirements.txt
