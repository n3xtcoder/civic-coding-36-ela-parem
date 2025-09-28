# Ela Parem Telegram Bot

An intelligent Telegram bot for educational video content delivery with AI-powered assessments and conversation management, deployed on Azure App Service.

## Features

- **AI-Powered Assessments**: Uses Mistral AI for intelligent conversation handling and placement testing
- **Video Management**: Integrates with Airtable for video content management
- **User State Management**: Tracks user progress through different learning levels
- **Conversation Context**: Maintains conversation history for better AI interactions
- **Caching System**: Optimized performance with intelligent caching
- **Lean Logging**: Production-ready logging with minimal noise
- **Azure Deployment**: Automated deployment from GitHub to Azure App Service

## Architecture

- **Bot Framework**: aiogram (async Telegram Bot API)
- **AI Service**: Mistral AI for conversations and assessments
- **Database**: Airtable for video content and user data
- **Caching**: In-memory caching for performance optimization
- **Logging**: Structured logging with file rotation
- **Deployment**: Azure App Service with GitHub Actions CI/CD

## Prerequisites

- Python 3.11+
- Azure Account
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Airtable API Key and Base ID
- Mistral AI API Key
- GitHub Repository

## Azure App Service Deployment

### 1. Azure Portal Setup

**Create App Service:**
1. Go to [Azure Portal](https://portal.azure.com)
2. Click "Create a resource" → "Web App"
3. Fill in details:
   - **Name**: `ela-parem-bot` (must be unique globally)
   - **Runtime stack**: `Python 3.11`
   - **Operating System**: `Linux`
   - **Region**: Choose closest to your users
   - **Pricing tier**: `B1 Basic` (minimum for production)

**Configure Deployment:**
1. Go to your App Service → "Deployment Center"
2. Choose "GitHub" as source
3. Select your repository and branch (`main` or `master`)
4. Azure will automatically set up GitHub Actions

### 2. Environment Variables Configuration

Go to "Configuration" → "Application settings" and add:

```bash
# Required Environment Variables
BOT_TOKEN=your_telegram_bot_token_here
AIRTABLE_API_KEY=your_airtable_api_key_here
AIRTABLE_BASE_ID=your_airtable_base_id_here
VIDEOS_TABLE_ID=your_videos_table_id_here
USERS_TABLE_ID=your_users_table_id_here
MESSAGES_TABLE_ID=your_messages_table_id_here
MISTRAL_API_KEY=your_mistral_api_key_here

# Azure-specific settings
ENVIRONMENT=production
LOG_LEVEL=INFO
WEBSITES_ENABLE_APP_SERVICE_STORAGE=true
```

### 3. GitHub Repository Setup

**Add GitHub Secrets:**
1. Go to your GitHub repo → Settings → Secrets and variables → Actions
2. Add `AZUREAPPSERVICE_PUBLISHPROFILE` with the publish profile from Azure

**Get Publish Profile:**
1. In Azure Portal → Your App Service → "Get publish profile"
2. Copy the entire XML content
3. Add it as `AZUREAPPSERVICE_PUBLISHPROFILE` secret in GitHub

### 4. Deploy

**Automatic Deployment:**
- Push code to your `main` branch
- GitHub Actions will automatically deploy to Azure
- Monitor deployment in "Actions" tab

**Manual Deployment:**
```bash
# Clone repository
git clone <your-github-repo-url>
cd 36_Ela_Parem

# Push to trigger deployment
git add .
git commit -m "Initial deployment"
git push origin main
```

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

### Azure Monitoring

**Application Insights:**
1. Enable Application Insights in Azure Portal
2. Monitor performance and errors
3. Set up alerts for critical issues

**Log Streaming:**
```bash
# Azure CLI
az webapp log tail --name ela-parem-bot --resource-group <resource-group>

# Or in Azure Portal → App Service → Log stream
```

**Health Monitoring:**
- Azure Portal → "Health check" shows bot status
- Monitor CPU, Memory, and Request metrics
- Set up alerts for downtime

### Scaling

**Scale Out (Horizontal):**
1. Go to "Scale out" in Azure Portal
2. Adjust instance count based on usage
3. Enable auto-scaling for traffic spikes

**Scale Up (Vertical):**
1. Go to "Scale up" in Azure Portal
2. Choose higher pricing tier for more resources
3. Consider Premium plans for production

## Troubleshooting

### Common Issues

**1. Deployment Fails:**
```bash
# Check GitHub Actions logs
# Go to GitHub → Actions → Failed workflow

# Check Azure deployment logs
az webapp log download --name ela-parem-bot --resource-group <resource-group>
```

**2. Bot Not Responding:**
- Check environment variables are set correctly in Azure
- Verify bot token is valid
- Check Azure App Service logs
- Test bot token: `curl "https://api.telegram.org/bot<TOKEN>/getMe"`

**3. Airtable Connection Issues:**
- Verify API key and base ID
- Check table IDs are correct
- Monitor Airtable API usage limits

**4. High Costs:**
- Monitor usage in Azure Portal
- Set up billing alerts
- Consider scaling down during low usage
- Use Free tier for development

### Debug Mode

Enable debug logging in Azure:
1. Go to Configuration → Application settings
2. Add `LOG_LEVEL=DEBUG`
3. Restart the app service

## Security Best Practices

1. **Never commit `.env` files** to version control
2. **Use Azure Key Vault** for sensitive production data
3. **Enable HTTPS** for webhook endpoints (if using webhooks)
4. **Set up monitoring alerts**
5. **Regular security updates**
6. **Use managed identity** for Azure resources

## Cost Optimization

**Development:**
- Use Free tier for testing
- Scale down when not in use

**Production:**
- **B1 Basic**: ~$13/month for production
- **S1 Standard**: ~$55/month for higher traffic
- **P1V2 Premium**: ~$83/month for auto-scaling

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
├── web.config            # Azure App Service configuration
├── startup.txt           # Azure startup script
├── .deployment           # Azure deployment configuration
├── .github/workflows/    # GitHub Actions workflows
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
- Review Azure App Service logs
- Monitor GitHub Actions deployment logs

---

**Note**: This bot is designed for educational purposes and should be used in accordance with Telegram's Terms of Service and Bot API guidelines.
