import streamlit as st
import osmnx as ox
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
import pandas as pd
from shapely.geometry import Point

# --- Page Config ---
st.set_page_config(page_title="Tangla Urban Analytics", layout="wide")

st.title("🏙️ Tangla Urban Land Use Mapper")
st.markdown("""
**Project:** Mapping Tangla, Udalguri (PIN: 784521).  
This tool highlights the 'Data Gap' in smaller Indian towns while providing a functional GIS baseline.
""")

# --- Sidebar Inputs ---
with st.sidebar:
    st.header("📍 Location Settings")
    # Defaulting to Tangla center coordinates
    lat_in = st.number_input("Target Latitude", value=26.6575, format="%.4f")
    lon_in = st.number_input("Target Longitude", value=91.9161, format="%.4f")
    label_name = st.text_input("Point Label", "Tangla Station/Market")
    
    st.header("Adjust Map Scope")
    buffer_dist = st.slider("Search Radius (meters)", 500, 5000, 2000)
    
    show_basemap = st.checkbox("Show Satellite/Basemap", value=True)
    run_map = st.button("Generate Reality Check")

# --- Spatial Logic ---
def get_assam_landuse(lat, lon, dist):
    # Tags specifically tuned for the Assam landscape
    tags = {
        "landuse": True, 
        "amenity": True, 
        "building": True, 
        "natural": ["water", "wood", "scrub", "wetland"],
        "railway": ["station", "rail"]
    }
    
    # Fetch data
    gdf = ox.features_from_point((lat, lon), tags=tags, dist=dist)
    
    # Custom Assam Classification Logic
    def classify_assam(row):
        # Priority 1: Tea Gardens (Crucial for Udalguri)
        if row.get('landuse') == 'orchard' or row.get('crop') == 'tea':
            return 'Tea Plantation'
        # Priority 2: Water & Wetlands
        if row.get('natural') in ['water', 'wetland'] or row.get('landuse') == 'pisciculture':
            return 'Water/Fishery'
        # Priority 3: Agriculture
        if row.get('landuse') in ['farmland', 'meadow']:
            return 'Agriculture (Paddy)'
        # Priority 4: Built Environment
        if pd.notnull(row.get('building')) or row.get('landuse') in ['residential', 'commercial', 'industrial']:
            return 'Built-up Area'
        # Priority 5: Infrastructure
        if pd.notnull(row.get('railway')):
            return 'Railway Infrastructure'
        
        return 'Unclassified/Vegetation'

    gdf['Category'] = gdf.apply(classify_assam, axis=1)
    return gdf

# --- Execution ---
if run_map:
    try:
        with st.spinner("Processing spatial queries for Tangla..."):
            # 1. Fetch and process
            gdf = get_assam_landuse(lat_in, lon_in, buffer_dist)
            gdf_projected = gdf.to_crs(epsg=3857) # For Contextily compatibility
            
            # 2. Setup Plot
            fig, ax = plt.subplots(figsize=(10, 10))
            
            # 3. Define Colors for Assam Context
            color_map = {
                'Tea Plantation': '#228B22',      # Forest Green
                'Water/Fishery': '#1E90FF',       # Dodger Blue
                'Agriculture (Paddy)': '#DAA520', # Goldenrod
                'Built-up Area': '#FF4500',       # Orange Red
                'Railway Infrastructure': '#333333', # Dark Grey
                'Unclassified/Vegetation': '#A9A9A9' # Silver
            }
            
            # 4. Plot layers
            gdf_projected.plot(
                column='Category', 
                ax=ax, 
                legend=True, 
                categorical=True,
                categories=list(color_map.keys()),
                color=[color_map.get(cat, '#A9A9A9') for cat in gdf_projected['Category']],
                alpha=0.7,
                legend_kwds={'loc': 'lower left', 'title': 'Land Use Type'}
            )
            
            # 5. Add Input Coordinate Label
            pt = gpd.GeoSeries([Point(lon_in, lat_in)], crs="EPSG:4326").to_crs(epsg=3857)
            pt.plot(ax=ax, color='yellow', edgecolor='black', markersize=100, marker='X', zorder=10)
            ax.annotate(label_name, xy=(pt.x[0], pt.y[0]), xytext=(8, 8), 
                        textcoords="offset points", fontsize=12, fontweight='bold', 
                        bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

            # 6. Basemap Logic
            if show_basemap:
                ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron)
            
            ax.set_axis_off()
            st.pyplot(fig)
            
            # 7. The "Kozhikode Style" Reality Check Analysis
            st.divider()
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Data Composition")
                counts = gdf['Category'].value_counts()
                st.bar_chart(counts)
                
            with col2:
                st.subheader("🧐 The Reality Check")
                missing_pct = (counts.get('Unclassified/Vegetation', 0) / len(gdf)) * 100
                st.warning(f"**{missing_pct:.1f}%** of features in this view are unclassified.")
                st.info("""
                **Planner's Note:** In Tangla, much of the 'Unclassified' data represents 
                informal residential clusters or small-scale tea smallholdings that 
                OSM volunteers haven't tagged yet.
                """)

    except Exception as e:
        st.error(f"Could not fetch data: {e}")
