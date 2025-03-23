import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Sustainable Business Analytics",
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
    get_nearby_businesses
)
from utils.achievements import get_all_achievements, initialize_achievements
from utils.auth import (
    init_session_state,
    login_user,
    register_user,
    logout_user,
    get_current_user
)
from utils.recommendations import generate_recommendations, format_recommendations_for_display, track_user_interaction

# Initialize session state for authentication and recommendations
init_session_state()
if 'last_recommendation_time' not in st.session_state:
    st.session_state.last_recommendation_time = None

if 'db_initialized' not in st.session_state:
    try:
        with st.spinner("Welcome to Sustainable Business Analytics! Stitching things up ;)"):
            init_database()
            initialize_achievements()
            st.session_state.db_initialized = True
    except Exception as e:
        st.error(f"Database error: {str(e)}")
        st.stop()

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
        ["All States"] + get_unique_states(),
        index=0,
        help="Filter businesses by state"
    )
    if state_filter != "All States":
        filters['state'] = state_filter

    # Category filter
    category_filter = st.selectbox(
        "🏷️ Business Category",
        ["All Categories"] + get_unique_categories(),
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

# Load data with pagination and filters
with st.spinner('Loading data...'):
    try:
        df, total_count = load_fashion_data(page=page, per_page=per_page, filters=filters)
        pages = -(-total_count // per_page)  # Ceiling division

        if len(df) == 0:
            st.warning("No businesses found matching your criteria.")
            st.stop()

        st.success(f'Showing {len(df)} of {total_count} businesses (Page {page} of {pages})')
    except Exception as e:
        st.error(f"Failed to load data: {str(e)}")
        st.stop()

# Get metrics summary
metrics = get_metrics_summary()

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
        df_sorted = df.sort_values(sort_map[sort_by], ascending=ascending)
    except Exception as e:
        st.error(f"Error sorting data: {str(e)}")
        df_sorted = df

    # Display businesses in a grid
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
                                try:
                                    track_user_interaction(
                                        user_id=st.session_state.user['id'],
                                        interaction_type="view_business",
                                        data={
                                            "business_id": business['id'],
                                            "category": business['category'],
                                            "sustainability_score": business['sustainability_score']
                                        }
                                    )
                                    # Update last recommendation time to trigger refresh on next tab view
                                    st.session_state.last_recommendation_time = None
                                except Exception as e:
                                    st.error(f"Failed to track interaction: {str(e)}")


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

            # Get list of cities with their states - do this once and store in state
            if 'city_state_list' not in st.session_state:
                cities = get_unique_cities()
                city_state_map = {}
                try:
                    for _, row in df.iterrows():
                        city_state_map[row['city']] = row['state']
                except Exception as e:
                    st.error(f"Error loading city data: {str(e)}")
                    city_state_map = {}

                # Create and sort city-state list once
                city_state_list = []
                for city in cities:
                    if city in city_state_map:
                        city_state_list.append(f"{city}, {city_state_map[city]}")
                st.session_state.city_state_list = sorted(city_state_list)

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
            # Create an empty map centered on the US
            fig = px.scatter_map(
                df,
                lat='latitude',
                lon='longitude',
                hover_name='brand_name',
                zoom=3,
                center=dict(lat=39.8283, lon=-98.5795),
                map_style="carto-positron"
            )
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
        with st.spinner('Searching nearby businesses...'):
            nearby = get_nearby_businesses(df, latitude, longitude, radius)

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

                # Filter by minimum score if specified
                if min_score_filter > 0:
                    nearby = nearby[nearby['sustainability_score'] >= min_score_filter]

                if len(nearby) > 0:
                    st.success(f"Found {len(nearby)} sustainable businesses within {radius} miles")

                    # Map visualization
                    fig = px.scatter_map(
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
                        map_style="carto-positron",
                        zoom=9,
                        center=dict(lat=latitude, lon=longitude)
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Display results in a grid
                    st.subheader("Nearby Businesses")
                    for i in range(0, len(nearby), 2):
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

                                        # Additional metrics in columns
                                        metric_cols = st.columns(2)
                                        with metric_cols[0]:
                                            st.metric("Eco Score", f"{business['eco_materials_score']:.1f}%")
                                        with metric_cols[1]:
                                            st.metric("Worker Welfare", f"{business['worker_welfare']:.1f}%")

                                        if business['website']:
                                            st.markdown(f"[🌐 Visit Website]({business['website']})")
                else:
                    st.warning(f"No businesses found with sustainability score ≥ {min_score_filter}")
            else:
                st.warning("No sustainable businesses found within the specified radius.")

with tab3:
    st.header("🏆 Sustainability Achievements")
    st.write("Earn badges by exploring and supporting sustainable businesses!")

    # Get all achievements and display them
    achievements = get_all_achievements()

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
                with st.spinner("Updating recommendations based on your recent interactions..."):
                    try:
                        raw_recommendations = generate_recommendations(
                            user_id=current_user['id'],
                            api_key=st.session_state.openai_api_key
                        )
                        recommendations = format_recommendations_for_display(raw_recommendations)
                        st.session_state.last_recommendation_time = current_time
                        st.session_state.current_recommendations = recommendations
                    except Exception as e:
                        st.error(f"Could not generate recommendations: {str(e)}")
                        recommendations = {
                            "business_recommendations": [],
                            "sustainability_tips": [],
                            "suggested_categories": []
                        }
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
        # Performance Analytics content
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

            # Scatter plot with multiple dimensions
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
            st.plotly_chart(fig, use_container_width=True)

        with metric_col2:
            st.subheader("Top Performers")
            top_10 = df.nlargest(10, selected_metric)

            for _, row in top_10.iterrows():
                with st.container():
                    st.markdown(f"**{row['brand_name']}** ({row['city']}, {row['state']})")
                    st.progress(row[selected_metric] / 100)
                    st.caption(f"{metric_options[selected_metric]}: {row[selected_metric]:.1f}%")

    with analytics_tab2:
        # Regional Analysis content
        region_col1, region_col2 = st.columns([1, 2])

        with region_col1:
            view_type = st.radio(
                "Select View",
                ["State Overview", "Category Distribution", "Performance Heatmap"]
            )

        with region_col2:
            if view_type == "State Overview":
                # Choropleth map
                fig = px.choropleth(
                    df.groupby('state')['sustainability_score'].mean().reset_index(),
                    locations='state',
                    locationmode="USA-states",
                    color='sustainability_score',
                    scope="usa",
                    color_continuous_scale="Viridis",
                    title="Average Sustainability Score by State"
                )
                st.plotly_chart(fig, use_container_width=True)

            elif view_type == "Category Distribution":
                # Category distribution by state
                category_dist = pd.crosstab(df['state'], df['category'])
                fig = px.bar(
                    category_dist,
                    title="Business Categories by State",
                    barmode='stack'
                )
                st.plotly_chart(fig, use_container_width=True)

            else:  # Performance Heatmap
                # Create correlation matrix of metrics
                correlation_metrics = [
                    'sustainability_score', 'eco_materials_score',
                    'carbon_footprint', 'water_usage', 'worker_welfare'
                ]
                corr_matrix = df[correlation_metrics].corr()

                fig = px.imshow(
                    corr_matrix,
                    title="Sustainability Metrics Correlation",
                    labels=dict(color="Correlation"),
                    color_continuous_scale="RdBu"
                )
                st.plotly_chart(fig, use_container_width=True)

# Footer section
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <p>Promoting sustainable businesses across the United States</p>
        <p><small>Data last updated: March 2025 | Contributing to a greener future 🌱</small></p>
    </div>
    """,
    unsafe_allow_html=True
)
st.markdown("---")
st.markdown("""
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
""", unsafe_allow_html=True)
