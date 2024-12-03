import os
import logging
import requests
import time
from datetime import datetime, timezone, timedelta, time
from telegram.ext import Application, CommandHandler
from dotenv import load_dotenv
from functools import wraps
import signal
import sys
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes, CallbackQueryHandler
import aiohttp
from telegram.error import TimedOut, NetworkError, RetryAfter
import backoff

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
class Config:
    COINGECKO_API_URL = "https://api.coingecko.com/api/v3/"
    FEAR_GREED_API = "https://api.alternative.me/fng/"
    COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY')
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    CACHE_TIMEOUT = 35  # minutes
    API_RATE_LIMIT_DELAY = 1  # seconds
    VERSION = "1.0.0"
    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 5
    MAX_RETRY_DELAY = 30
    NETWORK_TIMEOUT = 30

# Cache manager
class CacheManager:
    def __init__(self):
        self.cache = {}
        self.last_state = None

    def get(self, key):
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(minutes=Config.CACHE_TIMEOUT):
                return value
        return None

    def set(self, key, value):
        self.cache[key] = (value, datetime.now())

cache_manager = CacheManager()

# API request function
def make_coingecko_request(endpoint, params=None):
    headers = {
        "accept": "application/json",
        "x-cg-demo-api-key": Config.COINGECKO_API_KEY
    }
    
    try:
        response = requests.get(
            f"{Config.COINGECKO_API_URL}{endpoint}",
            headers=headers,
            params=params,
            timeout=10
        )
        import time as time_module
        time_module.sleep(Config.API_RATE_LIMIT_DELAY)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"API Request Error: {str(e)}")
        return None

# Cache decorator
def cache_with_timeout(timeout_minutes=35):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result)
            return result
        return wrapper
    return decorator

# Data fetching functions (same as in Flask app)
@cache_with_timeout(35)
def get_market_data():
    data = make_coingecko_request('global')
    if data and 'data' in data:
        return data['data']
    return {
        'market_cap_percentage': {'btc': 0},
        'total_market_cap': {'usd': 0}
    }

@cache_with_timeout(35)
def get_eth_btc_ratio():
    """Get the ETH/BTC ratio"""
    try:
        data = make_coingecko_request('simple/price', {
            'ids': 'ethereum,bitcoin',
            'vs_currencies': 'usd'
        })
        
        if data and 'ethereum' in data and 'bitcoin' in data:
            eth_price = data['ethereum']['usd']
            btc_price = data['bitcoin']['usd']
            return eth_price / btc_price
        return 0
    except Exception as e:
        logger.error(f"Error getting ETH/BTC ratio: {e}")
        return 0

@cache_with_timeout(35)
def get_fear_greed_index():
    """Get the Fear & Greed Index"""
    try:
        response = requests.get(Config.FEAR_GREED_API)
        data = response.json()
        return {
            'value': data['data'][0]['value'],
            'value_classification': data['data'][0]['value_classification']
        }
    except Exception as e:
        logger.error(f"Error getting fear & greed index: {e}")
        return {'value': '0', 'value_classification': 'Unknown'}

@cache_with_timeout(35)
def get_btc_monthly_roi():
    """Get Bitcoin's monthly ROI"""
    try:
        data = make_coingecko_request('coins/bitcoin/market_chart', {
            'vs_currency': 'usd',
            'days': '30',
            'interval': 'daily'
        })
        
        if data and 'prices' in data:
            start_price = data['prices'][0][1]
            end_price = data['prices'][-1][1]
            roi = ((end_price - start_price) / start_price) * 100
            return roi
        return 0
    except Exception as e:
        logger.error(f"Error calculating BTC monthly ROI: {e}")
        return 0

@cache_with_timeout(35)
def get_top10_alts_performance():
    """Get top 10 altcoins performance vs BTC"""
    try:
        # Get top 11 coins (including BTC)
        data = make_coingecko_request('coins/markets', {
            'vs_currency': 'btc',  # Price in BTC to compare against Bitcoin
            'order': 'market_cap_desc',
            'per_page': '11',
            'sparkline': 'false',
            'price_change_percentage': '30d'
        })
        
        if data:
            # Remove Bitcoin and get average performance
            alts_data = [coin for coin in data if coin['id'] != 'bitcoin']
            performances = [coin.get('price_change_percentage_30d_in_currency', 0) for coin in alts_data]
            # Filter out None values and calculate average
            valid_performances = [p for p in performances if p is not None]
            if valid_performances:
                return sum(valid_performances) / len(valid_performances)
        return 0
    except Exception as e:
        logger.error(f"Error calculating top 10 alts performance: {e}")
        return 0

@cache_with_timeout(35)
def get_altcoin_volume_dominance():
    """Get altcoin volume dominance percentage"""
    try:
        data = make_coingecko_request('global')
        if data and 'data' in data:
            total_volume = data['data']['total_volume']['usd']
            btc_volume = data['data']['total_volume']['btc']
            
            # Get BTC price to convert BTC volume to USD
            btc_data = make_coingecko_request('simple/price', {
                'ids': 'bitcoin',
                'vs_currencies': 'usd'
            })
            
            if btc_data and 'bitcoin' in btc_data:
                btc_price = btc_data['bitcoin']['usd']
                btc_volume_usd = btc_volume * btc_price
                
                # Calculate altcoin volume and dominance
                altcoin_volume = total_volume - btc_volume_usd
                volume_dominance = (altcoin_volume / total_volume) * 100
                return volume_dominance
        return 0
    except Exception as e:
        logger.error(f"Error calculating altcoin volume dominance: {e}")
        return 0

async def check_indicators():
    """Check all indicators and return a status message"""
    try:
        market_data = get_market_data()
        bitcoin_dominance = market_data['market_cap_percentage']['btc']
        eth_btc_ratio = get_eth_btc_ratio()
        fear_greed = get_fear_greed_index()
        btc_monthly_roi = get_btc_monthly_roi()
        top10_alts_perf = get_top10_alts_performance()
        volume_dominance = get_altcoin_volume_dominance()

        # Track which conditions are met
        conditions = {
            'BTC Dominance': (bitcoin_dominance < 45, bitcoin_dominance, "< 45%"),
            'ETH/BTC Ratio': (eth_btc_ratio > 0.07, eth_btc_ratio, "> 0.07"),
            'Fear & Greed': (int(fear_greed['value']) > 65, int(fear_greed['value']), "> 65"),
            'BTC Monthly ROI': (btc_monthly_roi < 0, btc_monthly_roi, "< 0%"),
            'Top 10 Alts Performance': (top10_alts_perf > 10, top10_alts_perf, "> 10%"),
            'Altcoin Volume': (volume_dominance > 60, volume_dominance, "> 60%")
        }

        # Check if we're in alt season
        is_alt_season = all(condition[0] for condition in conditions.values())

        # Create status message
        message = "🔄 Alt Season Indicators Update\n\n"
        message += f"{'🚀 Alt Season Likely!' if is_alt_season else '⏳ Not Alt Season Yet'}\n\n"
        message += f"✨ {sum(1 for condition in conditions.values() if condition[0])}/6 Conditions Met\n\n"
        message += "📊 Current Indicators:\n"
        for name, (is_met, value, target) in conditions.items():
            message += f"• {name}: {value:.2f} {'✅' if is_met else '❌'} (Target: {target})\n"
        
        # Add website link
        message += "\n📈 View detailed charts and analysis at https://www.thealtsignal.com"

        return message, is_alt_season, conditions

    except Exception as e:
        logger.error(f"Error checking indicators: {str(e)}")
        return "Error checking indicators", False, {}

async def send_daily_update(context):
    """Send daily update to the specified chat"""
    message, _, _ = await check_indicators()
    await context.bot.send_message(
        chat_id=Config.TELEGRAM_CHAT_ID,
        text=message
    )

async def monitor_changes(context):
    """Monitor for changes in indicators and alt season status"""
    message, is_alt_season, current_conditions = await check_indicators()
    
    # Initialize last conditions if needed
    if not hasattr(cache_manager, 'last_conditions'):
        cache_manager.last_conditions = current_conditions
        cache_manager.last_state = is_alt_season
        return

    # Check for changes in individual conditions
    changed_conditions = []
    for name, (is_met, value, target) in current_conditions.items():
        last_met = cache_manager.last_conditions[name][0]
        if last_met != is_met:
            status_emoji = "✅" if is_met else "❌"
            changed_conditions.append(
                f"{status_emoji} {name} "
                f"{'now meets' if is_met else 'no longer meets'} target {target}\n"
                f"Current value: {value:.2f}"
            )

    # Send alerts for changed conditions
    if changed_conditions:
        alert_message = "⚠️ Indicator Changes Detected!\n\n" + "\n\n".join(changed_conditions)
        await context.bot.send_message(
            chat_id=Config.TELEGRAM_CHAT_ID,
            text=alert_message
        )

    # Check for alt season status change
    if cache_manager.last_state != is_alt_season:
        await context.bot.send_message(
            chat_id=Config.TELEGRAM_CHAT_ID,
            text=f"🚨 Alt Season Status Change!\n\n{message}"
        )

    # Update cached states
    cache_manager.last_conditions = current_conditions
    cache_manager.last_state = is_alt_season

async def send_bot_status(application, status="start"):
    """Send bot status notification"""
    emoji = "🟢" if status == "start" else "🔴"
    status_text = "Online" if status == "start" else "Offline"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    message = (
        f"{emoji} Bot {status_text}\n"
        f"📊 Version: {Config.VERSION}\n"
        f"⏰ {timestamp}"
    )
    
    try:
        await application.bot.send_message(
            chat_id=Config.TELEGRAM_CHAT_ID,
            text=message
        )
    except Exception as e:
        logger.error(f"Failed to send bot status message: {e}")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Shutdown signal received")
    
    # Create an event loop to send the shutdown message
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Send offline notification
        loop.run_until_complete(send_bot_status(application, "stop"))
        logger.info("Shutdown message sent successfully")
    except Exception as e:
        logger.error(f"Error sending shutdown message: {e}")
    finally:
        loop.close()
        sys.exit(0)

# Add new function to check website status
async def check_website_status():
    """Check if thealtsignal.com is accessible"""
    url = "https://www.thealtsignal.com/"
    timeout = aiohttp.ClientTimeout(total=10)  # 10 seconds timeout
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return True, response.status, response.elapsed.total_seconds()
                else:
                    return False, response.status, 0
    except Exception as e:
        logger.error(f"Website check error: {str(e)}")
        return False, None, 0

# Add command handler
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /status command"""
    # Check if the user is authorized
    if str(update.effective_user.id) != os.getenv('ADMIN_USER_ID'):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    # Send initial message
    status_message = await update.message.reply_text("🔍 <i>Checking website status...</i>")
    
    # Check website status
    is_up, status_code, response_time = await check_website_status()
    
    if is_up:
        message = (
            "✅ Website Status Check\n\n"
            f"🌐 <a href='https://www.thealtsignal.com'>thealtsignal.com</a>\n"
            f"📊 Status Code: {status_code}\n"
            f"⚡ Response Time: {response_time:.2f}s"
        )
    else:
        message = (
            "❌ Website Status Check\n\n"
            f"🌐 <a href='https://www.thealtsignal.com'>thealtsignal.com</a>\n"
            f"⚠️ Status: {status_code if status_code is not None else 'Unreachable'}"
        )
    
    # Update the status message
    await status_message.edit_text(message)

# Add the manual status command and callback handler
async def manual_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /setstatus command"""
    # Check if the user is authorized
    if str(update.effective_user.id) != os.getenv('ADMIN_USER_ID'):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    # Create inline keyboard
    keyboard = [
        [
            InlineKeyboardButton("✅ Up", callback_data='status_up'),
            InlineKeyboardButton("❌ Down", callback_data='status_down'),
            InlineKeyboardButton("🔧 Maintenance", callback_data='status_maintenance')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Select website status:",
        reply_markup=reply_markup
    )

async def status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle status button callbacks"""
    query = update.callback_query
    await query.answer()
    
    # Check if the user is authorized
    if str(query.from_user.id) != os.getenv('ADMIN_USER_ID'):
        await query.edit_message_text("❌ You are not authorized to use this command.")
        return
    
    status_messages = {
        'status_up': {
            'emoji': '✅',
            'status': 'Online',
            'message': 'Website is up and running normally.'
        },
        'status_down': {
            'emoji': '❌',
            'status': 'Offline',
            'message': 'Website is currently down.'
        },
        'status_maintenance': {
            'emoji': '🔧',
            'status': 'Under Maintenance',
            'message': 'Website is undergoing scheduled maintenance.'
        }
    }
    
    status_info = status_messages.get(query.data)
    if status_info:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        message = (
            f"{status_info['emoji']} Website Status Update\n\n"
            f"🌐 https://www.thealtsignal.com\n"
            f"📊 Status: {status_info['status']}\n"
            f"💬 {status_info['message']}\n"
            f"⏰ {timestamp}"
        )
        
        # Edit the original message to remove buttons
        await query.edit_message_text(text=message)
        
        # Send the status update to the main channel if different from the command chat
        if str(query.message.chat.id) != Config.TELEGRAM_CHAT_ID:
            await context.bot.send_message(
                chat_id=Config.TELEGRAM_CHAT_ID,
                text=message
            )

def main():
    """Start the bot"""
    global application
    
    # Create application with custom settings
    application = (
        Application.builder()
        .token(Config.TELEGRAM_BOT_TOKEN)
        .connect_timeout(Config.NETWORK_TIMEOUT)
        .read_timeout(Config.NETWORK_TIMEOUT)
        .write_timeout(Config.NETWORK_TIMEOUT)
        .get_updates_connect_timeout(Config.NETWORK_TIMEOUT)
        .get_updates_read_timeout(Config.NETWORK_TIMEOUT)
        .get_updates_write_timeout(Config.NETWORK_TIMEOUT)
        .build()
    )

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Docker stop

    # Add command handlers
    application.add_handler(CommandHandler('status', status_command))
    application.add_handler(CommandHandler('setstatus', manual_status_command))
    application.add_handler(CallbackQueryHandler(status_callback, pattern='^status_'))

    # Add jobs
    job_queue = application.job_queue
    
    # Daily update at 8:00 AM EST (13:00 UTC)
    job_queue.run_daily(
        send_daily_update, 
        time=time(hour=13, minute=0, tzinfo=timezone.utc)
    )
    
    # Check for changes every hour
    job_queue.run_repeating(
        monitor_changes, 
        interval=timedelta(hours=1),
        first=60  # Start first check after 60 seconds
    )

    # Combined startup sequence
    async def startup_sequence(context):
        """Run startup sequence with status and initial check"""
        # Send startup message
        await send_bot_status(application, "start")
        
        # Wait 5 seconds
        await asyncio.sleep(5)
        
        # Do initial indicator check
        message, _, _ = await check_indicators()
        await context.bot.send_message(
            chat_id=Config.TELEGRAM_CHAT_ID,
            text=message
        )

    # Run startup sequence
    job_queue.run_once(startup_sequence, when=1)

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
