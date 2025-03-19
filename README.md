# Sustainable Fashion Analytics Platform 🌿

## Overview
A comprehensive Streamlit-based analytics platform that provides intelligent, personalized business sustainability insights across the USA. This platform helps users discover and analyze sustainable fashion businesses while offering AI-driven recommendations and interactive visualizations.

## Features
- 🏢 Nationwide sustainable business database
- 📍 Advanced location-based filtering with autocomplete
- 📊 Interactive data visualizations with Plotly
- 🤖 AI-driven personalized sustainability recommendations
- 📈 Comprehensive sustainability metrics tracking
- 🗄️ Scalable PostgreSQL database management
- 📑 Nested analytics tabs with dashboard, performance, and regional analysis
- 🔑 Customizable OpenAI API key integration

## Technologies Used
- Python 3.11
- Streamlit
- Plotly
- Pandas
- NumPy
- SQLAlchemy
- PostgreSQL
- LangChain
- OpenAI

## Setup Instructions

### Prerequisites
1. Python 3.11
2. PostgreSQL database
3. OpenAI API key (for recommendations)

### Installation Steps

1. Clone the repository:
```bash
git clone <your-repository-url>
cd sustainable-fashion-analytics
```

2. Install required packages:
```bash
pip install streamlit plotly pandas numpy sqlalchemy psycopg2-binary langchain langchain-openai openai
```

3. Set up environment variables:
Create a `.env` file in the root directory using the provided `.env.example` template:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/database_name
OPENAI_API_KEY=your_openai_api_key  # Optional, can be provided through UI
```

4. Initialize the database:
```bash
python -c "from models.database import init_database; init_database()"
```

5. Run the application:
```bash
streamlit run app.py --server.port 5000
```

The application will be available at `http://localhost:5000`

### OpenAI API Key Setup
To use the personalized recommendations feature:
1. Sign up/login at [OpenAI Platform](https://platform.openai.com)
2. Navigate to API Keys section
3. Create a new API key
4. Enter the key in the application's "Personalized Recommendations" tab

## Project Structure
```
├── app.py                 # Main Streamlit application
├── models/               
│   └── database.py       # Database models and initialization
├── utils/
│   ├── achievements.py   # Achievement system logic
│   ├── auth.py          # Authentication handling
│   ├── data_processor.py # Data processing utilities
│   └── recommendations.py # AI recommendation system
└── .streamlit/
    └── config.toml       # Streamlit configuration
```

## Features Overview

### Business Explorer
- Browse and filter sustainable businesses
- View detailed sustainability metrics
- Interactive sorting and filtering

### Location Search
- Search businesses by city or current location
- Radius-based filtering
- Interactive map visualization

### Achievements
- Track sustainability engagement
- Earn badges for exploring sustainable businesses
- View progress and rewards

### Personalized Recommendations
- AI-powered business recommendations
- Sustainability tips based on viewing history
- Category suggestions

### Analytics & Insights
- Comprehensive sustainability metrics
- Regional analysis
- Performance analytics
- Interactive visualizations

## Database Setup
1. Create a PostgreSQL database
2. Update the DATABASE_URL in your `.env` file
3. Run the database initialization script
4. The application will automatically create necessary tables and populate sample data

## Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Support
For any questions or issues, please open an issue in the GitHub repository.