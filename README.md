# Alt Season Indicators Telegram Bot

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)

A Telegram bot that monitors and alerts on various cryptocurrency market indicators to determine if we're in an "alt season" - a period when altcoins significantly outperform Bitcoin.

## Timing and Intervals

- Daily Update: 8:00 AM EST (13:00 UTC)
- Indicator Checks: Every hour
- Startup Sequence:
  1. Bot startup message (5 seconds after launch)
  2. First indicator check (60 seconds after launch)
  3. Regular hourly checks begin

## Features

  - Bitcoin Dominance
  - ETH/BTC Ratio
  - Fear & Greed Index
  - Bitcoin Monthly ROI
  - Top 10 Altcoin Performance
  - Volume Dominance
- Server-side caching to respect API limits
- Admin-only commands for website status management

## Indicator Logic

### Primary Indicators

1. **Bitcoin Dominance** (< 45%)
   - Measures Bitcoin's market cap as a percentage of total crypto market cap
   - Lower dominance suggests money flowing into altcoins
   - Historical alt seasons typically occur below 45%

2. **ETH/BTC Ratio** (> 0.07)
   - Measures Ethereum's strength against Bitcoin
   - Higher ratio indicates altcoin market strength
   - ETH often leads altcoin movements

3. **Fear & Greed Index** (> 65)
   - Market sentiment indicator from 0-100
   - Above 65 indicates "Greed" or "Extreme Greed"
   - Alt seasons typically occur during high greed periods

### Supporting Indicators

4. **BTC Monthly ROI** (< 0%)
   - Bitcoin's 30-day return on investment
   - Negative ROI suggests capital moving from BTC to alts
   - Helps confirm market rotation

5. **Top 10 Alts Performance** (> 10%)
   - Average 30-day performance of top 10 altcoins vs BTC
   - Strong outperformance indicates alt season momentum
   - Excludes Bitcoin from calculation

6. **Volume Dominance** (> 60%)
   - Percentage of total market volume in altcoins
   - High volume suggests active alt trading
   - Confirms market participation

## Bot Commands

- `/status` - Check website status (admin only)
- `/setstatus` - Manually update website status (admin only)
  - ✅ Up
  - ❌ Down
  - 🔧 Maintenance

## Setup and Installation

### Prerequisites
- Python 3.11+
- Docker (for containerized deployment)
- Telegram Bot Token
- CoinGecko API Key

### Environment Variables
Create a `.env` file with:

```env
# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
ADMIN_USER_ID=your_user_id

# CoinGecko API
COINGECKO_API_KEY=your_api_key
```

### Docker Deployment


Build the container
docker build -t alt-signal-bot .
Run the container
docker run -d \
--name alt-signal-bot \
--restart unless-stopped \
alt-signal-bot

### Docker Management

View logs
docker logs -f alt-signal-bot
Stop bot
docker stop alt-signal-bot
Start bot
docker start alt-signal-bot
Restart bot
docker restart alt-signal-bot

## Caching Strategy

- Default cache duration: 35 minutes
- API rate limit delay: 1 second between calls
- Server-side caching to respect API limits

## Data Sources & APIs

### CoinGecko API Endpoints
- Global market data
- Simple price queries
- Market charts
- Top coins by market cap

### External APIs
- Fear & Greed Index (alternative.me)
- Website status monitoring

## Requirements

Listed in `requirements.txt`:

python-telegram-bot==20.7
requests==2.31.0
python-dotenv==1.0.0
aiohttp==3.9.1


## Rate Limits

- CoinGecko Free API: 10-30 calls/minute
- Alternative.me: No strict limit
- Cached responses: 35 minutes

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.