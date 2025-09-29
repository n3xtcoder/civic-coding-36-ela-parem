# Ela Parem Telegram Bot

An intelligent Telegram bot for educational video content delivery with AI-powered assessments and conversation management, deployed on Render.

## Features

- **AI-Powered Assessments**: Uses Mistral AI for intelligent conversation handling and placement testing
- **Video Management**: Integrates with Airtable for video content management
- **User State Management**: Tracks user progress through different learning levels
- **Conversation Context**: Maintains conversation history for better AI interactions
- **Caching System**: Optimized performance with intelligent caching
- **Lean Logging**: Production-ready logging with minimal noise
- **Render Deployment**: Automated deployment from GitHub to Render Web Service

## Architecture

- **Bot Framework**: aiogram (async Telegram Bot API)
- **AI Service**: Mistral AI for conversations and assessments
- **Database**: Airtable for video content and user data
- **Caching**: In-memory caching for performance optimization
- **Logging**: Structured logging with file rotation
- **Deployment**: Render Web Service with automatic GitHub integration

## Prerequisites

- Python 3.11+
- Render Account (free tier available)
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Airtable API Key and Base ID
- Mistral AI API Key
- GitHub Repository

## Render Deployment

### 1. Render Dashboard Setup

**Create Background Worker:**
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Background Worker"
3. Connect your GitHub repository
4. Fill in service details:
   - **Name**: `ela-parem-bot`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Plan**: `Free` (for development) or `Starter` (for production)

### 2. Environment Variables Configuration

In the Render dashboard, go to "Environment" tab and add:

```bash
# Required Environment Variables
BOT_TOKEN=your_telegram_bot_token_here
AIRTABLE_API_KEY=your_airtable_api_key_here
AIRTABLE_BASE_ID=your_airtable_base_id_here
VIDEOS_TABLE_ID=your_videos_table_id_here
USERS_TABLE_ID=your_users_table_id_here
MESSAGES_TABLE_ID=your_messages_table_id_here
MISTRAL_API_KEY=your_mistral_api_key_here

# Render-specific settings
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### 3. Automatic Deployment

**GitHub Integration:**
- Render automatically deploys when you push to your connected branch
- Default branch is `main` or `master`
- Each push triggers a new deployment
- Monitor deployments in the Render dashboard

**Manual Deployment:**
```bash
# Push to trigger deployment
git add .
git commit -m "Deploy to Render"
git push origin main
```

### 4. Service Configuration

**Advanced Settings:**
- **Auto-Deploy**: Enabled by default
- **Restart Policy**: Automatic restart on failure
- **Health Check**: Not applicable for background workers
- **Custom Domains**: Not available for background workers

## Local Development

### 1. Setup Local Environment

```bash
# Clone repository
git clone <your-github-repo-url>
cd 36_Ela_Parem

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp env.example .env
```

### 2. Configure Local Environment

Edit `.env` file with your credentials:

```bash
# Bot Configuration
BOT_TOKEN=your_telegram_bot_token_here

# Airtable Configuration
AIRTABLE_API_KEY=your_airtable_api_key_here
AIRTABLE_BASE_ID=your_airtable_base_id_here
VIDEOS_TABLE_ID=your_videos_table_id_here
USERS_TABLE_ID=your_users_table_id_here
MESSAGES_TABLE_ID=your_messages_table_id_here

# Mistral AI Configuration
MISTRAL_API_KEY=your_mistral_api_key_here

# Local development settings
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

### 3. Run Locally

```bash
# Test configuration
python -c "from config import Config; print('Config valid:', Config.validate_config())"

# Run the bot
python main.py
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `BOT_TOKEN` | Telegram bot token from BotFather | Yes |
| `AIRTABLE_API_KEY` | Airtable API key | Yes |
| `AIRTABLE_BASE_ID` | Airtable base ID | Yes |
| `VIDEOS_TABLE_ID` | Airtable videos table ID | Yes |
| `USERS_TABLE_ID` | Airtable users table ID | Yes |
| `MESSAGES_TABLE_ID` | Airtable messages table ID | Yes |
| `MISTRAL_API_KEY` | Mistral AI API key | Yes |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | No |
| `ENVIRONMENT` | Environment (development/production) | No |

### Airtable Schema

**Videos Table:**
- `Title` (Single line text)
- `Description` (Long text)
- `Question` (Long text)
- `YouTube Link` (URL)
- `Level` (Single select: Entry, Beginner, Intermediate, Advanced)
- `Video Number` (Number)
- `Understanding Benchmark` (Long text)

**Users Table:**
- `Telegram ID` (Number)
- `Level` (Single select)
- `Video Number` (Number)
- `State` (Single select)

**Messages Table:**
- `Role` (Single select: User, Bot)
- `Message` (Long text)
- `Video` (Link to Videos table)

## Monitoring and Maintenance

### Render Monitoring

**Service Dashboard:**
1. Monitor background worker status in Render dashboard
2. View real-time logs and metrics
3. Track deployment history and status
4. Monitor resource usage and performance
5. Check worker restart history

**Log Streaming:**
- Real-time logs available in Render dashboard
- Filter logs by level (INFO, WARNING, ERROR)
- Download logs for offline analysis
- Log retention varies by plan

**Health Monitoring:**
- Render automatically monitors background worker health
- Automatic restarts on crashes or failures
- Uptime monitoring and alerts
- Performance metrics tracking
- Worker process monitoring

### Scaling

**Free Tier Limitations:**
- Background worker sleeps after 15 minutes of inactivity
- Cold starts may take 30-60 seconds
- Limited to 750 hours/month
- No custom domains
- Worker may restart if idle for too long

**Paid Plans:**
- **Starter**: $7/month - Always running background worker
- **Standard**: $25/month - More resources, better performance
- **Pro**: $85/month - High availability, auto-scaling

## Troubleshooting

### Common Issues

**1. Deployment Fails:**
```bash
# Check Render deployment logs
# Go to Render Dashboard → Your Service → Logs

# Common build issues:
# - Missing dependencies in requirements.txt
# - Python version mismatch
# - Environment variables not set
```

**2. Bot Not Responding:**
- Check environment variables are set correctly in Render
- Verify bot token is valid
- Check Render background worker logs for errors
- Test bot token: `curl "https://api.telegram.org/bot<TOKEN>/getMe"`
- Ensure background worker is not sleeping (Free tier limitation)
- Check if worker process crashed and restarted

**3. Background Worker Sleeping (Free Tier):**
- Free tier background workers sleep after 15 minutes of inactivity
- Bot may not respond immediately after waking up
- Consider upgrading to Starter plan for always-on worker
- Implement periodic health checks to keep worker active

**4. Airtable Connection Issues:**
- Verify API key and base ID
- Check table IDs are correct
- Monitor Airtable API usage limits
- Check network connectivity in Render background worker logs

**5. Worker Process Issues:**
- Monitor worker restart frequency in Render dashboard
- Check for memory leaks or resource exhaustion
- Review error logs for Python exceptions
- Ensure proper error handling in bot code

### Debug Mode

Enable debug logging in Render:
1. Go to Render Dashboard → Your Background Worker → Environment
2. Add `LOG_LEVEL=DEBUG`
3. Redeploy the background worker

## Security Best Practices

1. **Never commit `.env` files** to version control
2. **Use Render Environment Variables** for sensitive production data
3. **Enable HTTPS** for webhook endpoints (if using webhooks)
4. **Set up monitoring alerts**
5. **Regular security updates**
6. **Use environment-specific configurations**

## Cost Optimization

**Development:**
- Use Free tier for testing
- Background worker sleeps after inactivity (saves resources)
- 750 hours/month limit on Free tier
- Monitor worker restart patterns

**Production:**
- **Free**: $0/month - Good for development and low traffic
- **Starter**: $7/month - Always running background worker
- **Standard**: $25/month - Better performance, more resources
- **Pro**: $85/month - High availability, auto-scaling

## Code Structure

```
├── main.py                 # Main bot application
├── config.py              # Configuration management
├── models.py              # Data models and types
├── airtable_service.py    # Airtable integration
├── conversation_service.py # AI conversation handling
├── utils.py               # Utility functions
├── logger.py              # Logging system
├── cache.py               # Caching system
├── requirements.txt       # Dependencies
├── services/              # Additional service modules
└── env.example           # Environment variables template
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review Render background worker logs
- Monitor deployment status in Render dashboard
- Check worker restart history for stability issues

---

**Note**: This bot is designed for educational purposes and should be used in accordance with Telegram's Terms of Service and Bot API guidelines.
