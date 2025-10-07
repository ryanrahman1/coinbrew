# CoinBrew Backend

CoinBrew is a mock cryptocurrency trading platform backend. It provides endpoints to manage users, coins, trades, portfolios, and real-time-ish coin price updates.

---

## Features

### Authentication
- User registration with hashed passwords.
- Login with credential verification.
- Retrieve user info without exposing passwords.

### Coins
- Create new coins with optional images.
- Fetch coin info by symbol.
- Get coin history over specific ranges (`12h`, `24h`, `1w`, `max`).
- List all coins with filtering, sorting, and pagination.

### Trading & Wallets
- Buy and sell coins.
- Automatic balance updates and wallet management.
- Prevents overspending or overselling.

### Price Calculation
- Prices update automatically every 6 hours based on supply, demand, and recent trades.
- Price history is recorded for charting and portfolio tracking.
- Manual price updates possible after trades for immediate reflection.

### Portfolio & Leaderboard
- Retrieve user portfolios including total value (USD + coins).
- Get leaderboard of top users by portfolio value.
- Access detailed user profiles including coins created and portfolio.

### Background Jobs
- Automatic coin price updates every 6 hours.
- Background job ensures price history is continuously updated for accurate graphing.

---

## Technologies

- **Framework:** FastAPI
- **Database:** Supabase (PostgreSQL)
- **Storage:** Supabase storage for coin images
- **Image Handling:** Users can upload coin images from their browser; images are processed with lossless compression to minimize file size before being stored in Supabase storage.
- **Authentication:** Hashed passwords (bcrypt)
- **Scheduler:** APScheduler for background jobs
- **Languages & Libraries:** Python 3, Pydantic, APScheduler, Supabase Python client, Pillow (for image processing)

---

## API Endpoints (Main)

| Path | Method | Description |
|------|--------|-------------|
| `/auth/register` | POST | Register a new user |
| `/auth/login` | POST | Login user |
| `/auth/user/{user_id}` | GET | Get user info |
| `/coins/create` | POST | Create a new coin (optional image upload) |
| `/coins/all` | POST | Get all coins with filters & pagination |
| `/coins/{symbol}` | GET | Get coin info by symbol |
| `/coins/{symbol}/history` | GET | Get coin history by range |
| `/coins/buy` | POST | Buy coins |
| `/coins/sell` | POST | Sell coins |
| `/coins/portfolio/{user_id}` | GET | Get user portfolio |
| `/coins/leaderboard` | GET | Get top users by portfolio value |
| `/coins/profile/{user_id}` | GET | Get user profile |
| `/coins/wallets/{user_id}` | GET | Get all wallets for a user |

---

## Price Algorithm

- Prices are calculated using a mix of:
  - **Supply & circulating coins**
  - **Recent trade activity**
  - **Smoothing & damping** to avoid wild fluctuations
- Formula considers net demand vs supply, smoothing factor (EMA), and caps extreme changes to ±20% per update.
- Ensures realistic-looking coin price movement.


**Ryan Rahman** © 2025  
