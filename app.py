import streamlit as st

# Page configuration - Set this first to avoid warnings
st.set_page_config(
    page_title="Sustainable Business Analytics USA",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

import plotly.express as px
import pandas as pd
from utils.data_processor import (
    load_fashion_data,
    init_database,
    get_unique_cities,
    get_unique_states,
    get_unique_categories,
    get_metrics_summary,
    get_nearby_businesses,
)
from utils.achievements import get_all_achievements, initialize_achievements
from utils.auth import (
    init_session_state,
    login_user,
    register_user,
    logout_user,
    get_current_user,
)
from utils.recommendations import generate_recommendations, format_recommendations_for_display, track_user_interaction

# Initialize session state for authentication and recommendations
init_session_state()
if 'last_recommendation_time' not in st.session_state:
    st.session_state.last_recommendation_time = None
    
# One-time database initialization with proper error handling
if 'db_initialized' not in st.session_state:
    try:
        with st.spinner("Welcome to Sustainable Business Analytics! Getting things ready :)"):
            init_database()
            initialize_achievements()
            st.session_state.db_initialized = True
    except Exception as e:
        st.error(f"Failed to initialize database: {str(e)}")
        st.stop()

# Cache expensive operations
@st.cache_data(ttl=3600, hash_funcs={pd.DataFrame: lambda _: None})  # Cache for 1 hour
def get_cached_metrics_summary():
    return get_metrics_summary()

@st.cache_data(ttl=3600, hash_funcs={pd.DataFrame: lambda _: None})  # Cache for 1 hour
def get_cached_unique_states():
    return get_unique_states()

@st.cache_data(ttl=3600, hash_funcs={pd.DataFrame: lambda _: None})  # Cache for 1 hour
def get_cached_unique_categories():
    return get_unique_categories()

@st.cache_data(ttl=3600, hash_funcs={pd.DataFrame: lambda _: None})  # Cache for 1 hour
def get_cached_achievements():
    return get_all_achievements()

@st.cache_data(ttl=3600, hash_funcs={pd.DataFrame: lambda _: None})  # Cache for 1 hour
def get_cached_cities():
    cities = get_unique_cities()
    return cities

@st.cache_data(hash_funcs={pd.DataFrame: lambda _: None})
def placeholder_function():
    pass

@st.cache_data(ttl=3600, hash_funcs={pd.DataFrame: lambda _: None})
def prepare_city_state_list(df):
    # Convert df to a hashable object like a tuple or string
    city_state_map = {}
    try:
        for _, row in df.iterrows():
            city_state_map[row['city']] = row['state']
    except Exception as e:
        st.error(f"Error loading city data: {str(e)}")
        city_state_map = {}
    
    # Create and sort city-state list
    cities = get_cached_cities()
    city_state_list = []
    for city in cities:
        if city in city_state_map:
            city_state_list.append(f"{city}, {city_state_map[city]}")
    return sorted(city_state_list)

# Authentication sidebar
with st.sidebar:
    if not st.session_state.authenticated:
        st.title("Login / Register")
        tab1, tab2 = st.tabs(["Login", "Register"])

        with tab1:
            with st.form("login_form"):
                login_email = st.text_input("Email", key="login_email")
                login_password = st.text_input("Password", type="password", key="login_password")
                login_submitted = st.form_submit_button("Login")

                if login_submitted:
                    if login_user(login_email, login_password):
                        st.success("Successfully logged in!")
                        st.rerun()
                    else:
                        st.error("Invalid email or password")

        with tab2:
            with st.form("register_form"):
                reg_email = st.text_input("Email", key="reg_email")
                reg_username = st.text_input("Username", key="reg_username")
                reg_password = st.text_input("Password", type="password", key="reg_password")
                reg_submitted = st.form_submit_button("Register")

                if reg_submitted:
                    if register_user(reg_email, reg_username, reg_password):
                        st.success("Registration successful! Please login.")
                        st.rerun()

    else:
        st.title(f"Welcome, {st.session_state.user['username']}!")
        if st.button("Logout"):
            logout_user()
            st.rerun()

# Rest of the sidebar filters
with st.sidebar:
    st.title("Search & Filters")

    # Initialize filters
    filters = {}

    # Search box
    search_query = st.text_input("🔍 Search by business name")
    if search_query:
        filters['search'] = search_query

    # State filter
    state_filter = st.selectbox(
        "📍 Select State",
        ["All States"] + get_cached_unique_states(),
        index=0,
        help="Filter businesses by state"
    )
    if state_filter != "All States":
        filters['state'] = state_filter

    # Category filter
    category_filter = st.selectbox(
        "🏷️ Business Category",
        ["All Categories"] + get_cached_unique_categories(),
        index=0,
        help="Filter by business category"
    )
    if category_filter != "All Categories":
        filters['category'] = category_filter
        if st.session_state.authenticated:
            track_user_interaction(
                user_id=st.session_state.user['id'],
                interaction_type="filter_category",
                data={"category": category_filter}
            )

    # Score range
    st.write("📊 Sustainability Score Range")
    min_score, max_score = st.slider(
        "Select range",
        0, 100, (0, 100),
        help="Filter businesses by sustainability score"
    )
    if min_score > 0:
        filters['min_score'] = min_score
    if max_score < 100:
        filters['max_score'] = max_score

    # Pagination
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        page = st.number_input("Page", min_value=1, value=1)
    with col2:
        per_page = st.selectbox("Per page", [25, 50, 100], index=0)

# Load data with pagination and filters - keep this outside of caching as it depends on user input
with st.spinner('Loading data...'):
    try:
        # Create a cache key based on filters to improve caching
        filter_key = str(filters) + f"_page{page}_perpage{per_page}"
        
        # Use st.cache_data for the data load with specific key
        @st.cache_data(ttl=300, show_spinner=False, hash_funcs={pd.DataFrame: lambda _: filter_key})  # Cache for 5 minutes
        def load_cached_data(filter_key):
            # Parse the filter key back to its components
            # This is a simplified version - you'd need to parse the actual filter string
            return load_fashion_data(page=page, per_page=per_page, filters=filters)
        
        df, total_count = load_cached_data(filter_key)
        pages = -(-total_count // per_page)  # Ceiling division

        if len(df) == 0:
            st.warning("No businesses found matching your criteria.")
            st.stop()

        st.success(f'Showing {len(df)} of {total_count} businesses (Page {page} of {pages})')
    except Exception as e:
        st.error(f"Failed to load data: {str(e)}")
        st.stop()

# Get metrics summary (cached)
metrics = get_cached_metrics_summary()

# Main content
st.title("🌿 Sustainable Business Analytics USA")
st.write("Discover and analyze sustainable businesses across the United States")

# Create tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏢 Business Explorer",
    "📍 Location Search",
    "🏆 Achievements",
    "🎯 Personalized Recommendations",
    "📊 Learn More"
])

with tab1:
    st.header("Sustainable Business Explorer")
    # Display businesses in a grid with sorting options
    sort_col, metric_col = st.columns([2, 2])
    with sort_col:
        sort_by = st.selectbox(
            "Sort by",
            ["Brand Name", "Sustainability Score", "Eco Materials Score", "Worker Welfare", "City"],
            help="Choose how to sort the businesses"
        )
    with metric_col:
        ascending = st.checkbox("Ascending order", value=False)

    # Sort dataframe
    sort_map = {
        "Brand Name": "brand_name",
        "Sustainability Score": "sustainability_score",
        "Eco Materials Score": "eco_materials_score",
        "Worker Welfare": "worker_welfare",
        "City": "city"
    }

    try:
        # More efficient sorting directly on the dataframe
        sort_column = sort_map.get(sort_by, "brand_name")
        df_sorted = df.sort_values(sort_column, ascending=ascending)
    except Exception as e:
        st.error(f"Error sorting data: {str(e)}")
        df_sorted = df

    # Display businesses in a grid
    # Use container to improve rendering performance
    grid_container = st.container()
    with grid_container:
        # Create rows of 3 columns
        for i in range(0, len(df_sorted), 3):
            cols = st.columns(3)
            for j, col in enumerate(cols):
                if i + j < len(df_sorted):
                    business = df_sorted.iloc[i + j]
                    with col:
                        with st.container():
                            st.subheader(business['brand_name'])
                            st.caption(f"📍 {business['city']}, {business['state']}")

                            # Create a metrics container
                            metrics_container = st.container()
                            with metrics_container:
                                st.progress(business['sustainability_score'] / 100)

                            # Website link
                            if business['website']:
                                st.markdown(f"[🌐 Visit Website]({business['website']})")

                            # Show details in an expandable container
                            with st.expander("📊 Details", expanded=False):
                                st.write("#### About")
                                st.write(business['description'])

                                st.write("#### Certifications")
                                cert_text = " • ".join([f"✓ {cert}" for cert in business['certifications']])
                                st.write(cert_text)

                                st.write("#### Sustainability Metrics")
                                metrics_md = f"""
                                - 🌱 **Eco Materials:** {business['eco_materials_score']:.1f}%
                                - 🌡️ **Carbon Footprint:** {business['carbon_footprint']:.1f}%
                                - 💧 **Water Usage:** {business['water_usage']:.1f}%
                                - 👥 **Worker Welfare:** {business['worker_welfare']:.1f}%
                                """
                                st.markdown(metrics_md)

                                st.write("#### Location")
                                st.write(f"📍 {business['city']}, {business['state']} {business['zip_code']}")

                                if st.session_state.authenticated:
                                    # Batch interactions instead of tracking each one individually
                                    if 'pending_interactions' not in st.session_state:
                                        st.session_state.pending_interactions = []
                                    
                                    st.session_state.pending_interactions.append({
                                        "user_id": st.session_state.user['id'],
                                        "interaction_type": "view_business",
                                        "data": {
                                            "business_id": business['id'],
                                            "category": business['category'],
                                            "sustainability_score": business['sustainability_score']
                                        }
                                    })
                                    
                                    # Update last recommendation time to trigger refresh on next tab view
                                    st.session_state.last_recommendation_time = None

with tab2:
    st.header("Location-Based Search")

    # Location selection method
    location_method = st.radio(
        "Choose location method",
        ["🏙️ Search by City", "📍 Use Current Location", "🗺️ Select from Map"],
        horizontal=True
    )

    col1, col2 = st.columns([2, 1])

    with col1:
        if location_method == "🏙️ Search by City":
            # Initialize session state for city selection if not exists
            if 'selected_city' not in st.session_state:
                st.session_state.selected_city = None

            # Get city-state list using the cached function
            if 'city_state_list' not in st.session_state:
                st.session_state.city_state_list = prepare_city_state_list(df)

            # Use the stored city-state list
            if st.session_state.city_state_list:
                selected_location = st.selectbox(
                    "Search for a city",
                    options=st.session_state.city_state_list,
                    index=None,
                    placeholder="Choose a city...",
                    help="Type to search for a city. Results will update as you type.",
                    key="city_selectbox"
                )

                if selected_location:
                    try:
                        # Split city and state from selection
                        city, state = selected_location.split(", ")

                        # Verify the selected city exists in our data
                        city_data = df[
                            (df['city'] == city) &
                            (df['state'] == state)
                        ]

                        if not city_data.empty:
                            latitude = float(city_data.iloc[0]['latitude'])
                            longitude = float(city_data.iloc[0]['longitude'])
                            st.success(f"Found location: {city}, {state}")
                            st.session_state.selected_city = selected_location
                        else:
                            st.warning("Could not find coordinates for the selected city")
                            latitude, longitude = None, None
                    except Exception as e:
                        st.error(f"Error processing city selection: {str(e)}")
                        latitude, longitude = None, None
            else:
                st.warning("No cities available in the database. Please check the data loading.")

        elif location_method == "📍 Use Current Location":
            st.info("Click below to use your current location")
            if st.button("📍 Use My Location", type="primary"):
                # Add JavaScript to get user's location
                st.markdown(
                    """
                    <script>
                    if (navigator.geolocation) {
                        navigator.geolocation.getCurrentPosition(function(position) {
                            const lat = position.coords.latitude;
                            const lon = position.coords.longitude;
                            window.parent.postMessage({
                                type: "streamlit:setComponentValue",
                                value: [lat, lon]
                            }, "*");
                        });
                    }
                    </script>
                    """,
                    unsafe_allow_html=True
                )
                latitude, longitude = 40.7128, -74.0060  # Default to NYC

        else:  # Select from Map
            st.info("Click on the map to select your location")
            
            # Only create map when needed and cache it
            @st.cache_data(ttl=3600, hash_funcs={pd.DataFrame: lambda _: None})

            def create_map(df_sample):
                # Use a sample of data points for better performance
                fig = px.scatter_mapbox(
                    df_sample,
                    lat='latitude',
                    lon='longitude',
                    hover_name='brand_name',
                    zoom=3,
                    center=dict(lat=39.8283, lon=-98.5795),
                    mapbox_style="carto-positron"
                )
                return fig
            
            # Sample the dataframe for better map performance
            map_sample = df.sample(min(len(df), 100)) if len(df) > 100 else df
            fig = create_map(map_sample)
            st.plotly_chart(fig, use_container_width=True)
            
            # Use the clicked point's coordinates
            latitude, longitude = 40.7128, -74.0060  # Default to NYC

    with col2:
        radius = st.slider(
            "Search Radius (miles)",
            min_value=5,
            max_value=500,
            value=50,
            help="Select the radius to search for nearby businesses"
        )

        st.markdown("### Quick Filters")
        min_score_filter = st.slider(
            "Minimum Sustainability Score",
            0, 100, 0,
            help="Filter nearby businesses by minimum sustainability score"
        )

    # Search button
    if st.button("🔍 Find Sustainable Businesses", type="primary"):
        # Cache the nearby business search for the same location and radius
        @st.cache_data(ttl=600, show_spinner=False, hash_funcs={pd.DataFrame: lambda _: f"{lat}_{lon}_{rad}_{min_score}"})
        def get_cached_nearby(df, lat, lon, rad, min_score):
            nearby = get_nearby_businesses(df, lat, lon, rad)
            if min_score > 0:
                nearby = nearby[nearby['sustainability_score'] >= min_score]
            return nearby
        
        with st.spinner('Searching nearby businesses...'):
            nearby = get_cached_nearby(df, latitude, longitude, radius, min_score_filter)

            if len(nearby) > 0:
                if st.session_state.authenticated:
                    track_user_interaction(
                        user_id=st.session_state.user['id'],
                        interaction_type="search_location",
                        data={
                            "state": nearby.iloc[0]['state'],
                            "sustainability_score": nearby.iloc[0]['sustainability_score']
                        }
                    )

                st.success(f"Found {len(nearby)} sustainable businesses within {radius} miles")

                # Map visualization
                fig = px.scatter_mapbox(
                    nearby,
                    lat='latitude',
                    lon='longitude',
                    hover_name='brand_name',
                    hover_data={
                        'sustainability_score': ':.1f',
                        'distance': ':.1f',
                        'city': True,
                        'state': True,
                        'category': True,
                        'latitude': False,
                        'longitude': False
                    },
                    color='sustainability_score',
                    size='sustainability_score',
                    title='Nearby Sustainable Businesses',
                    mapbox_style="carto-positron",
                    zoom=9,
                    center=dict(lat=latitude, lon=longitude)
                )
                st.plotly_chart(fig, use_container_width=True)

                # Display results in a grid - potentially use pagination here for large result sets
                st.subheader("Nearby Businesses")
                
                # Show only first 10 businesses by default to improve rendering speed
                display_limit = min(10, len(nearby))
                
                for i in range(0, display_limit, 2):
                    cols = st.columns(2)
                    for j, col in enumerate(cols):
                        if i + j < display_limit:
                            business = nearby.iloc[i + j]
                            with col:
                                with st.expander(
                                    f"📍 {business['brand_name']} ({business['city']}, {business['state']})"
                                ):
                                    st.metric("Distance", f"{business['distance']:.1f} miles")
                                    st.metric("Sustainability Score", f"{business['sustainability_score']:.1f}%")
                                    st.metric("Category", business['category'])

                                    # Additional metrics in columns
                                    metric_cols = st.columns(2)
                                    with metric_cols[0]:
                                        st.metric("Eco Score", f"{business['eco_materials_score']:.1f}%")
                                    with metric_cols[1]:
                                        st.metric("Worker Welfare", f"{business['worker_welfare']:.1f}%")

                                    if business['website']:
                                        st.markdown(f"[🌐 Visit Website]({business['website']})")
                
                # Show a "Load More" button if there are more businesses to display
                if len(nearby) > display_limit:
                    if st.button(f"Show all {len(nearby)} businesses"):
                        for i in range(display_limit, len(nearby), 2):
                            cols = st.columns(2)
                            for j, col in enumerate(cols):
                                if i + j < len(nearby):
                                    business = nearby.iloc[i + j]
                                    with col:
                                        with st.expander(
                                            f"📍 {business['brand_name']} ({business['city']}, {business['state']})"
                                        ):
                                            st.metric("Distance", f"{business['distance']:.1f} miles")
                                            st.metric("Sustainability Score", f"{business['sustainability_score']:.1f}%")
                                            st.metric("Category", business['category'])
                                            
                                            if business['website']:
                                                st.markdown(f"[🌐 Visit Website]({business['website']})")
                    
            else:
                st.warning("No sustainable businesses found within the specified radius.")

with tab3:
    st.header("🏆 Sustainability Achievements")
    st.write("Earn badges by exploring and supporting sustainable businesses!")

    # Get all achievements and display them - with caching
    achievements = get_cached_achievements()

    # Group achievements by category
    categories = {
        "exploration": "🔍 Explorer Badges",
        "sustainability": "🌱 Eco Warrior Badges",
        "community": "👥 Community Leader Badges"
    }

    # Display achievements by category
    for category, title in categories.items():
        st.write(f"### {title}")
        category_achievements = [a for a in achievements if a['category'] == category]

        if category_achievements:
            # Create a grid of badges
            num_cols = min(3, len(category_achievements))
            if num_cols > 0:
                cols = st.columns(num_cols)
                for idx, achievement in enumerate(category_achievements):
                    with cols[idx % num_cols]:
                        st.markdown(achievement['icon'], unsafe_allow_html=True)
                        st.markdown(f"**{achievement['name']}**")
                        st.markdown(achievement['description'])
                        st.markdown(f"🌟 {achievement['points']} points")
        else:
            st.info(f"No {category} badges available yet. Keep exploring to unlock new achievements!")

with tab4:
    st.header("🎯 Personalized Sustainability Recommendations")
    current_user = get_current_user()

    if not current_user:
        st.info("Please login to view your personalized recommendations based on your interests and interactions.")
        st.write("Once logged in, we'll analyze your browsing patterns to suggest:")
        st.markdown("""
        - 🏢 Businesses that match your interests
        - 🌱 Sustainability tips tailored to your preferences
        - 📚 Categories you might want to explore
        """)
    else:
        # OpenAI API Key Input Section
        api_key_instructions = """
        To get an OpenAI API key, go to the OpenAI platform, log in or create an account, navigate to the API Keys section, and click "Create new secret key".

        Here's a more detailed breakdown:
        1. Go to the OpenAI Platform: Visit the OpenAI platform website.
        2. Log In or Sign Up: If you already have an account, log in. Otherwise, create a new account.
        3. Navigate to API Keys: Once logged in, go to the "API Keys" section in your account dashboard.
        4. Create a New Key: Click the button that says "+ Create new secret key".
        5. Save the Key: Important: Save the newly generated API key securely, as you will not be able to view it again after closing the window.
        6. Paste the Key here.
        """

        # Initialize session state for API key
        if 'openai_api_key' not in st.session_state:
            st.session_state.openai_api_key = None

        col1, col2 = st.columns([3, 1])
        with col1:
            api_key = st.text_input(
                "Enter your OpenAI API Key to get personalized recommendations",
                type="password",
                help=api_key_instructions,
                key="api_key_input"
            )
        with col2:
            if st.button("📝 Set API Key"):
                if api_key:
                    st.session_state.openai_api_key = api_key
                    st.success("API Key set successfully!")
                else:
                    st.error("Please enter an API key")

        if not st.session_state.openai_api_key:
            st.warning("Please provide your OpenAI API key to view personalized recommendations.")
        else:
            current_time = pd.Timestamp.now()
            last_time = st.session_state.last_recommendation_time

            # Check if we need to refresh recommendations
            if last_time is None:
                # Cache recommendations for a user - improves performance on repeated tab views
                @st.cache_data(ttl=1800, show_spinner=False, hash_funcs={pd.DataFrame: lambda _: f"rec_{current_user['id']}"})  # Cache for 30 minutes
                def get_cached_recommendations(user_id, api_key):
                    try:
                        raw_recommendations = generate_recommendations(
                            user_id=user_id,
                            api_key=api_key
                        )
                        return format_recommendations_for_display(raw_recommendations)
                    except Exception as e:
                        st.error(f"Could not generate recommendations: {str(e)}")
                        return {
                            "business_recommendations": [],
                            "sustainability_tips": [],
                            "suggested_categories": []
                        }
                
                with st.spinner("Updating recommendations based on your recent interactions..."):
                    recommendations = get_cached_recommendations(
                        current_user['id'], 
                        st.session_state.openai_api_key
                    )
                    st.session_state.last_recommendation_time = current_time
                    st.session_state.current_recommendations = recommendations
            else:
                recommendations = st.session_state.current_recommendations

            # Display recommendations in an organized way
            col1, col2 = st.columns([2, 1])

            with col1:
                st.write("#### Recommended Business Focus Areas")
                if recommendations["business_recommendations"]:
                    for rec in recommendations["business_recommendations"]:
                        with st.expander(f"💡 {rec['type'].title()} Recommendation"):
                            st.write(rec['recommendation'])
                            st.caption(f"Why? {rec['reason']}")
                else:
                    st.info("View some businesses to get personalized recommendations!")

            with col2:
                st.write("#### Sustainability Tips")
                if recommendations["sustainability_tips"]:
                    for tip in recommendations["sustainability_tips"]:
                        st.info(f"🌱 {tip}")
                else:
                    st.info("Interact with more businesses to get sustainability tips!")

                st.write("#### Explore Categories")
                if recommendations["suggested_categories"]:
                    for category in recommendations["suggested_categories"]:
                        st.button(f"📁 {category}", key=f"cat_{category}")
                else:
                    st.info("Explore more businesses to discover new categories!")

            # Add refresh button
            if st.button("🔄 Refresh Recommendations"):
                st.session_state.last_recommendation_time = None
                st.experimental_rerun()
    
with tab5:
    st.header("📊 Sustainability Analytics & Insights")

    # Dashboard Overview (shown by default)
    st.subheader("Dashboard Overview")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Businesses", f"{metrics['total_businesses']:,}")
    with col2:
        st.metric("States Coverage", f"{metrics['states_coverage']} states")
    with col3:
        st.metric("Avg Sustainability", f"{metrics['avg_sustainability']:.1f}%")
    with col4:
        st.metric("Top Category", max(metrics['top_categories'].items(), key=lambda x: x[1])[0])
    with col5:
        st.metric("Businesses Displayed", len(df))

    # Create nested tabs for analytics
    analytics_tab1, analytics_tab2 = st.tabs([
        "📈 Performance Analytics",
        "🗺️ Regional Analysis"
    ])

    with analytics_tab1:
        # Performance Analytics content - cache the chart generation
        metric_col1, metric_col2 = st.columns([2, 1])

        with metric_col1:
            # Interactive metric selection
            metric_options = {
                'sustainability_score': 'Overall Sustainability',
                'eco_materials_score': 'Eco Materials',
                'carbon_footprint': 'Carbon Footprint',
                'water_usage': 'Water Usage',
                'worker_welfare': 'Worker Welfare'
            }

            selected_metric = st.selectbox(
                "Select metric to analyze",
                list(metric_options.keys()),
                format_func=lambda x: metric_options[x]
            )

            # Cache the scatter plot generation based on the selected metric
            @st.cache_data(ttl=600, hash_funcs={pd.DataFrame: lambda _: f"{selected_metric}_scatterplot"})
            def generate_scatter_plot(df, selected_metric):
                fig = px.scatter(
                    df,
                    x='sustainability_score',
                    y=selected_metric,
                    size='sustainability_score',
                    color='category',
                    hover_name='brand_name',
                    hover_data={
                        'city': True,
                        'state': True,
                        selected_metric: ':.1f',
                        'sustainability_score': ':.1f'
                    },
                    title=f'{metric_options[selected_metric]} Analysis',
                    labels={
                        'sustainability_score': 'Overall Sustainability Score',
                        selected_metric: metric_options[selected_metric]
                    }
                )
                fig.update_layout(height=600)
                return fig
            
            fig = generate_scatter_plot(df, selected_metric)
            st.plotly_chart(fig, use_container_width=True)

        with metric_col2:
            st.subheader("Top Performers")
            
            # More efficient top performers calculation
            @st.cache_data(ttl=600, hash_funcs={pd.DataFrame: lambda _: None})
            def get_top_performers(df, metric, n=10):
                return df.nlargest(n, metric)
                
            top_10 = get_top_performers(df, selected_metric)

            for _, row in top_10.iterrows():
                with st.container():
                    st.markdown(f"**{row['brand_name']}** ({row['city']}, {row['state']})")
                    st.progress(row[selected_metric] / 100)
                    st.caption(f"{metric_options[selected_metric]}: {row[selected_metric]:.1f}%")

    with analytics_tab2:
    # Regional Analysis content
    # Cache computation-heavy operations
        @st.cache_data(hash_funcs={pd.DataFrame: lambda _: None})
        def get_state_avg_sustainability():
            return df.groupby('state')['sustainability_score'].mean().reset_index()
        
        @st.cache_data(hash_funcs={pd.DataFrame: lambda _: None})
        def get_category_distribution():
            return pd.crosstab(df['state'], df['category'])
        
        @st.cache_data(hash_funcs={pd.DataFrame: lambda _: None})
        def get_correlation_matrix(metrics):
            return df[metrics].corr()
    
    # Define the metrics list once to avoid recreation
    correlation_metrics = [
        'sustainability_score', 'eco_materials_score',
        'carbon_footprint', 'water_usage', 'worker_welfare'
    ]
    
    region_col1, region_col2 = st.columns([1, 2])
    
    with region_col1:
        view_type = st.radio(
            "Select View",
            ["State Overview", "Category Distribution", "Performance Heatmap"],
            key="region_view_type"  # Add unique key to improve session state handling
        )
    
    with region_col2:
        if view_type == "State Overview":
            # Get cached data instead of recomputing
            state_avg = get_state_avg_sustainability()
            
            # Create figure only once when needed
            fig = px.choropleth(
                state_avg,
                locations='state',
                locationmode="USA-states",
                color='sustainability_score',
                scope="usa",
                color_continuous_scale="Viridis",
                title="Average Sustainability Score by State"
            )
            # Optimize rendering
            fig.update_layout(margin={"r":0,"t":30,"l":0,"b":0})
            st.plotly_chart(fig, use_container_width=True, config={'staticPlot': False})
            
        elif view_type == "Category Distribution":
            # Get cached data
            category_dist = get_category_distribution()
            
            fig = px.bar(
                category_dist,
                title="Business Categories by State",
                barmode='stack'
            )
            # Optimize layout and rendering
            fig.update_layout(margin={"r":0,"t":30,"l":0,"b":0})
            st.plotly_chart(fig, use_container_width=True, config={'staticPlot': False})
            
        else:  # Performance Heatmap
            # Get cached correlation matrix
            corr_matrix = get_correlation_matrix(correlation_metrics)
            
            fig = px.imshow(
                corr_matrix,
                title="Sustainability Metrics Correlation",
                labels=dict(color="Correlation"),
                color_continuous_scale="RdBu"
            )
            # Optimize layout
            fig.update_layout(margin={"r":0,"t":30,"l":0,"b":0})
            st.plotly_chart(fig, use_container_width=True, config={'staticPlot': False})

# Footer section
# Use st.cache_data to store the HTML content
@st.cache_data
def get_footer_html():
    return {
        "main_footer": """
        <div style='text-align: center'>
            <p>Promoting sustainable businesses across the United States</p>
            <p><small>Data last updated: March 2025 | Contributing to a greener future 🌱</small></p>
        </div>
        """,
        "data_sources": """
        <div style='text-align: center'>
            <p><small>Data Sources:</small></p>
            <p><small>
            - Company information collected from official company websites and sustainability reports
            - Sustainability metrics compiled from third-party certifications and company disclosures
            - Geographic data sourced from public business registries
            - Last updated: March 2025
            </small></p>
            <p><small>Note: This is a demonstration dataset created for educational purposes.</small></p>
        </div>
        """
    }

# Create a container for the footer to better control layout and rendering
footer_container = st.container()

with footer_container:
    # Get cached HTML content
    footer_html = get_footer_html()
    
    # Use divider instead of markdown for the separator lines
    st.divider()
    
    # Main footer
    st.markdown(
        footer_html["main_footer"],
        unsafe_allow_html=True
    )
    
    st.divider()
    
    # Data sources
    st.markdown(
        footer_html["data_sources"],
        unsafe_allow_html=True
    )