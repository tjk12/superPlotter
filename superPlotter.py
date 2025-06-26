import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.offline import plot
import json
import numpy as np

def superPlotter(data, x="date", y="price", color="quality", filter="location", 
                title="Interactive Scatter Plot", output_file="interactive_plot.html"):
    """
    Create an enhanced Plotly scatter plot with custom checkbox filtering and flexible y-axis configuration.
    Now supports multiple datasets with tabbed interface and flexible multi-column faceting!
    
    Parameters:
    - data: pandas DataFrame OR dict of {str: pandas DataFrame} for multiple datasets
    - x: column name for x-axis
    - y: flexible y-axis specification:
         * string: single column name (creates one plot)
         * list: multiple column names (creates faceted subplots)
         * dict: for multi-dataset, maps dataset_name -> y_spec where y_spec can be string or list
    - color: column name for color grouping
    - filter: column name for checkbox filtering
    - title: plot title (or base title for multiple datasets)
    - output_file: output HTML filename
    """
    
    # Handle both single DataFrame and dictionary of DataFrames
    if isinstance(data, pd.DataFrame):
        datasets = {"Main": data}
        single_dataset = True
        # For single dataset, y can be string or list
        if isinstance(y, dict):
            raise ValueError("For single dataset, y cannot be a dictionary. Use string or list.")
        y_config = {"Main": y}
    elif isinstance(data, dict):
        datasets = data
        single_dataset = False
        # For multi-dataset, y must be a dict mapping dataset names to y specs
        if isinstance(y, dict):
            y_config = y
        else:
            # If y is string or list, apply to all datasets
            y_config = {dataset_name: y for dataset_name in datasets.keys()}
    else:
        raise ValueError("Data must be either a pandas DataFrame or a dictionary of DataFrames")
    
    # Normalize y_config to ensure all values are lists
    facets_per_dataset = {}
    max_facets = 0
    
    for dataset_name, y_spec in y_config.items():
        if isinstance(y_spec, str):
            facets_per_dataset[dataset_name] = [y_spec]
        elif isinstance(y_spec, list):
            facets_per_dataset[dataset_name] = y_spec
        else:
            raise ValueError(f"y specification for dataset '{dataset_name}' must be string or list, got {type(y_spec)}")
        
        max_facets = max(max_facets, len(facets_per_dataset[dataset_name]))
    
    # Validate all datasets have required columns
    for dataset_name, df in datasets.items():
        required_cols = [x, color, filter] + facets_per_dataset[dataset_name]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Dataset '{dataset_name}' missing columns: {missing_cols}")
    
    # Get all unique values across all datasets for consistent color mapping
    all_color_values = set()
    all_filter_values = set()
    
    for dataset_name, df in datasets.items():
        all_color_values.update(df[color].unique())
        all_filter_values.update(df[filter].unique())
    
    # Sort for consistency
    all_color_values = sorted(list(all_color_values))
    all_filter_values = sorted(list(all_filter_values))
    
    # Create consistent color mapping across all datasets
    color_palette = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
        '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5'
    ]
    color_mapping = {}
    for i, color_val in enumerate(all_color_values):
        color_mapping[color_val] = color_palette[i % len(color_palette)]
    
    # Prepare data for JavaScript
    datasets_json = {}
    for dataset_name, df in datasets.items():
        datasets_json[dataset_name] = df.to_json(orient='records')
    
    color_mapping_json = json.dumps(color_mapping)
    facets_per_dataset_json = json.dumps(facets_per_dataset)
    
    # Calculate max subplot layout
    subplot_cols = min(3, max_facets)
    subplot_rows = (max_facets + subplot_cols - 1) // subplot_cols
    
    # Create the HTML template with embedded JavaScript
    html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.26.0/plotly.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .main-container {{
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        .tabs-container {{
            background: white;
            border-radius: 8px 8px 0 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .tabs {{
            display: flex;
            border-bottom: 2px solid #e0e0e0;
            margin: 0;
            padding: 0;
        }}
        .tab {{
            background: #f8f9fa;
            border: none;
            padding: 12px 24px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            color: #666;
            border-radius: 8px 8px 0 0;
            margin-right: 2px;
            transition: all 0.3s ease;
        }}
        .tab:hover {{
            background: #e9ecef;
            color: #333;
        }}
        .tab.active {{
            background: white;
            color: #007bff;
            border-bottom: 2px solid #007bff;
            margin-bottom: -2px;
        }}
        .content-container {{
            display: flex;
            gap: 20px;
            background: white;
            border-radius: 0 0 8px 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 20px;
        }}
        .controls {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            min-width: 200px;
            max-width: 250px;
            height: fit-content;
        }}
        .plot-container {{
            flex: 1;
        }}
        .filter-section {{
            margin-bottom: 20px;
        }}
        .filter-title {{
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
            font-size: 16px;
        }}
        .checkbox-item {{
            margin: 8px 0;
            display: flex;
            align-items: center;
        }}
        .checkbox-item input[type="checkbox"] {{
            margin-right: 8px;
            transform: scale(1.1);
        }}
        .checkbox-item label {{
            cursor: pointer;
            font-size: 14px;
            color: #555;
        }}
        .select-all-btn {{
            background: #007bff;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            margin-right: 5px;
        }}
        .select-all-btn:hover {{
            background: #0056b3;
        }}
        .deselect-all-btn {{
            background: #6c757d;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
        }}
        .deselect-all-btn:hover {{
            background: #545b62;
        }}
        #plotDiv {{
            width: 100%;
            height: {600 if max_facets == 1 else max(400, 300 * subplot_rows)}px;
        }}
        .tab-content {{
            display: none;
        }}
        .tab-content.active {{
            display: block;
        }}
    </style>
</head>
<body>
    <div class="main-container">
        {"" if single_dataset else '''
        <div class="tabs-container">
            <div class="tabs" id="tabsContainer">
            </div>
        </div>
        '''}
        
        <div class="content-container">
            <div class="controls">
                <div class="filter-section">
                    <div class="filter-title">Filter by {filter.title()}</div>
                    <div style="margin-bottom: 10px;">
                        <button class="select-all-btn" onclick="selectAll()">Select All</button>
                        <button class="deselect-all-btn" onclick="deselectAll()">Deselect All</button>
                    </div>
                    <div id="filterCheckboxes"></div>
                </div>
            </div>
            <div class="plot-container">
                <div id="plotDiv"></div>
            </div>
        </div>
    </div>

    <script>
        // Data from Python
        const allDatasets = {json.dumps(datasets_json)};
        const filterColumn = '{filter}';
        const xColumn = '{x}';
        const colorColumn = '{color}';
        const facetsPerDataset = {facets_per_dataset_json};
        const allFilterValues = {json.dumps(all_filter_values)};
        const maxSubplotCols = {subplot_cols};
        const maxSubplotRows = {subplot_rows};
        const singleDataset = {json.dumps(single_dataset)};
        const baseTitle = '{title}';
        
        // Use the consistent color mapping from Python
        const colorMap = {color_mapping_json};
        
        // Current active dataset
        let currentDatasetName = Object.keys(allDatasets)[0];
        let currentData = JSON.parse(allDatasets[currentDatasetName]);
        let currentFacets = facetsPerDataset[currentDatasetName];
        
        // Initialize tabs if multiple datasets
        function initializeTabs() {{
            if (singleDataset) return;
            
            const tabsContainer = document.getElementById('tabsContainer');
            tabsContainer.innerHTML = '';
            
            Object.keys(allDatasets).forEach((datasetName, index) => {{
                const tab = document.createElement('button');
                tab.className = 'tab';
                tab.textContent = datasetName;
                tab.onclick = () => switchDataset(datasetName);
                if (index === 0) tab.classList.add('active');
                tabsContainer.appendChild(tab);
            }});
        }}
        
        // Switch between datasets
        function switchDataset(datasetName) {{
            // Update active tab
            document.querySelectorAll('.tab').forEach(tab => {{
                tab.classList.remove('active');
                if (tab.textContent === datasetName) {{
                    tab.classList.add('active');
                }}
            }});
            
            // Update current dataset
            currentDatasetName = datasetName;
            currentData = JSON.parse(allDatasets[datasetName]);
            currentFacets = facetsPerDataset[datasetName];
            
            // Update filter checkboxes based on current dataset
            updateFilterCheckboxes();
            
            // Update plot
            updatePlot();
        }}
        
        // Update filter checkboxes based on current dataset
        function updateFilterCheckboxes() {{
            const container = document.getElementById('filterCheckboxes');
            container.innerHTML = '';
            
            // Get unique filter values for current dataset
            const currentFilterValues = [...new Set(currentData.map(row => row[filterColumn]))].sort();
            
            currentFilterValues.forEach(value => {{
                const div = document.createElement('div');
                div.className = 'checkbox-item';
                
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.id = `filter_${{value}}`;
                checkbox.value = value;
                checkbox.checked = true;
                checkbox.addEventListener('change', updatePlot);
                
                const label = document.createElement('label');
                label.htmlFor = `filter_${{value}}`;
                label.textContent = value;
                
                div.appendChild(checkbox);
                div.appendChild(label);
                container.appendChild(div);
            }});
        }}
        
        // Group data by color for plotting
        function groupDataByColor(data) {{
            const groups = {{}};
            
            data.forEach(row => {{
                const colorValue = row[colorColumn];
                
                if (!groups[colorValue]) {{
                    groups[colorValue] = [];
                }}
                groups[colorValue].push(row);
            }});
            
            return groups;
        }}
        
        // Create plot traces with multi-column faceting support
        function createPlotTraces(data) {{
            const colorGroups = groupDataByColor(data);
            const traces = [];
            
            // Calculate subplot layout for current dataset
            const numFacets = currentFacets.length;
            const subplotCols = Math.min(3, numFacets);
            const subplotRows = Math.ceil(numFacets / subplotCols);
            
            // Create traces for each y-column (facet) and color combination
            currentFacets.forEach((yColumn, facetIndex) => {{
                Object.keys(colorGroups).forEach(colorValue => {{
                    const groupData = colorGroups[colorValue];
                    
                    // Calculate subplot position
                    let xaxis = 'x';
                    let yaxis = 'y';
                    
                    if (numFacets > 1) {{
                        const row = Math.floor(facetIndex / subplotCols) + 1;
                        const col = (facetIndex % subplotCols) + 1;
                        
                        if (row > 1 || col > 1) {{
                            const axisNum = (row - 1) * subplotCols + col;
                            xaxis = axisNum === 1 ? 'x' : `x${{axisNum}}`;
                            yaxis = axisNum === 1 ? 'y' : `y${{axisNum}}`;
                        }}
                    }}
                    
                    const trace = {{
                        x: groupData.map(row => row[xColumn]),
                        y: groupData.map(row => row[yColumn]),
                        mode: 'markers',
                        type: 'scatter',
                        name: colorValue,
                        legendgroup: colorValue,
                        showlegend: facetIndex === 0, // Only show legend for first facet
                        xaxis: xaxis,
                        yaxis: yaxis,
                        marker: {{
                            color: colorMap[colorValue],
                            size: 8,
                            line: {{
                                width: 1,
                                color: 'rgba(0,0,0,0.2)'
                            }}
                        }},
                        hovertemplate: `<b>${{colorValue}}</b><br>` +
                                      `{x}: %{{x}}<br>` +
                                      `${{yColumn}}: %{{y}}<br>` +
                                      `{filter}: %{{customdata[0]}}<br>` +
                                      '<extra></extra>',
                        customdata: groupData.map(row => [row[filterColumn]])
                    }};
                    traces.push(trace);
                }});
            }});
            
            return traces;
        }}
        
        // Update plot based on selected filters
        function updatePlot() {{
            const selectedFilters = [];
            
            // Get currently available filter values for this dataset
            const currentFilterValues = [...new Set(currentData.map(row => row[filterColumn]))].sort();
            
            currentFilterValues.forEach(value => {{
                const checkbox = document.getElementById(`filter_${{value}}`);
                if (checkbox && checkbox.checked) {{
                    selectedFilters.push(value);
                }}
            }});
            
            // Filter data
            const filteredData = currentData.filter(row => 
                selectedFilters.includes(row[filterColumn])
            );
            
            // Create new traces
            const traces = createPlotTraces(filteredData);
            
            // Create dynamic title
            const plotTitle = singleDataset ? baseTitle : `${{baseTitle}} - ${{currentDatasetName}}`;
            
            // Calculate subplot layout for current dataset
            const numFacets = currentFacets.length;
            const subplotCols = Math.min(3, numFacets);
            const subplotRows = Math.ceil(numFacets / subplotCols);
            
            // Create layout with subplots if multi-column faceting
            let layout = {{
                title: plotTitle,
                hovermode: 'closest',
                showlegend: true
            }};
            
            if (numFacets > 1) {{
                // Create subplot layout based on current dataset's facet columns
                layout.grid = {{
                    rows: subplotRows,
                    columns: subplotCols,
                    pattern: 'independent'
                }};
                
                // Add axis labels for each subplot
                currentFacets.forEach((yColumn, index) => {{
                    const row = Math.floor(index / subplotCols) + 1;
                    const col = (index % subplotCols) + 1;
                    
                    const axisNum = (row - 1) * subplotCols + col;
                    let xaxisKey = axisNum === 1 ? 'xaxis' : `xaxis${{axisNum}}`;
                    let yaxisKey = axisNum === 1 ? 'yaxis' : `yaxis${{axisNum}}`;
                    
                    layout[xaxisKey] = {{
                        title: row === subplotRows ? '{x}' : '',
                        anchor: yaxisKey.replace('yaxis', 'y')
                    }};
                    layout[yaxisKey] = {{
                        title: col === 1 ? yColumn : '',
                        anchor: xaxisKey.replace('xaxis', 'x')
                    }};
                    
                    // Add subplot titles
                    if (!layout.annotations) layout.annotations = [];
                    layout.annotations.push({{
                        text: yColumn,
                        showarrow: false,
                        x: (col - 0.5) / subplotCols,
                        y: 1 - (row - 1) / subplotRows + 0.02,
                        xref: 'paper',
                        yref: 'paper',
                        xanchor: 'center',
                        yanchor: 'bottom',
                        font: {{ size: 14, color: '#333', weight: 'bold' }}
                    }});
                }});
            }} else {{
                layout.xaxis = {{ title: '{x}' }};
                layout.yaxis = {{ title: currentFacets[0] }};
            }}
            
            // Update plot
            Plotly.newPlot('plotDiv', traces, layout);
        }}
        
        // Select all checkboxes
        function selectAll() {{
            const currentFilterValues = [...new Set(currentData.map(row => row[filterColumn]))].sort();
            currentFilterValues.forEach(value => {{
                const checkbox = document.getElementById(`filter_${{value}}`);
                if (checkbox) checkbox.checked = true;
            }});
            updatePlot();
        }}
        
        // Deselect all checkboxes
        function deselectAll() {{
            const currentFilterValues = [...new Set(currentData.map(row => row[filterColumn]))].sort();
            currentFilterValues.forEach(value => {{
                const checkbox = document.getElementById(`filter_${{value}}`);
                if (checkbox) checkbox.checked = false;
            }});
            updatePlot();
        }}
        
        // Initialize
        initializeTabs();
        updateFilterCheckboxes();
        updatePlot();
    </script>
</body>
</html>
"""
    
    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    print(f"Interactive plot saved to {output_file}")
    return output_file

# Example usage and demo
if __name__ == "__main__":
    # Create sample data for multiple datasets with multiple numeric columns
    np.random.seed(42)
    
    # Dataset 1: Stock data with multiple metrics
    dates1 = pd.date_range('2023-01-01', periods=100)
    stock_data = {
        'date': dates1,
        'price': np.random.normal(100, 15, 100) + np.random.normal(0, 3, 100).cumsum(),
        'volume': np.random.normal(1000000, 200000, 100),
        'market_cap': np.random.normal(50000000, 10000000, 100),
        'quality': np.random.choice(['High', 'Medium', 'Low'], 100),
        'location': np.random.choice(['New York', 'London', 'Tokyo'], 100),
    }
    
    # Dataset 2: Crypto data with different metrics
    dates2 = pd.date_range('2023-01-01', periods=120)
    crypto_data = {
        'date': dates2,
        'price': np.random.normal(50, 20, 120) + np.random.normal(0, 8, 120).cumsum(),
        'volume': np.random.normal(500000, 100000, 120),
        'market_cap': np.random.normal(25000000, 5000000, 120),
        'volatility': np.random.normal(0.05, 0.02, 120),
        'quality': np.random.choice(['High', 'Medium', 'Low'], 120),
        'location': np.random.choice(['New York', 'London', 'Tokyo', 'Seoul'], 120),
    }
    
    # Dataset 3: Commodity data with limited metrics
    dates3 = pd.date_range('2023-01-01', periods=80)
    commodity_data = {
        'date': dates3,
        'price': np.random.normal(200, 25, 80) + np.random.normal(0, 4, 80).cumsum(),
        'volume': np.random.normal(2000000, 400000, 80),
        'quality': np.random.choice(['High', 'Medium', 'Low'], 80),
        'location': np.random.choice(['New York', 'London', 'Singapore'], 80),
    }
    
    # Create DataFrames
    datasets = {
        'Stocks': pd.DataFrame(stock_data),
        'Crypto': pd.DataFrame(crypto_data),
        'Commodities': pd.DataFrame(commodity_data)
    }
    
    # EXAMPLE 1: Multi-dataset with different y configurations per dataset
    print("=== EXAMPLE 1: Multi-dataset with custom y per dataset ===")
    superPlotter(datasets, 
                x="date", 
                y={
                    'Stocks': ['price', 'volume', 'market_cap'],       # 3 subplots
                    'Crypto': ['price', 'volume', 'volatility'],      # 3 subplots (no market_cap)
                    'Commodities': ['price', 'volume']                # 2 subplots only
                },
                color="quality", 
                filter="location",
                title="Custom Multi-Metric Dashboard",
                output_file="custom_multi_dataset_demo.html")
    
    # EXAMPLE 2: Multi-dataset with same y configuration for all
    print("\n=== EXAMPLE 2: Multi-dataset with same y for all ===")
    superPlotter(datasets, 
                x="date", 
                y=['price', 'volume'],  # Apply to all datasets
                color="quality", 
                filter="location",
                title="Unified Multi-Dataset Dashboard",
                output_file="unified_multi_dataset_demo.html")
    
    # EXAMPLE 3: Single dataset with multiple y columns (faceting)
    print("\n=== EXAMPLE 3: Single dataset with faceting ===")
    superPlotter(datasets['Stocks'], 
                x="date", 
                y=['price', 'volume', 'market_cap'],  # List creates facets
                color="quality", 
                filter="location",
                title="Stock Analysis Dashboard",
                output_file="single_dataset_faceted_demo.html")
    
    # EXAMPLE 4: Single dataset with single y column (traditional plot)
    print("\n=== EXAMPLE 4: Single dataset traditional plot ===")
    superPlotter(datasets['Stocks'], 
                x="date", 
                y="price",  # String creates single plot
                color="quality", 
                filter="location",
                title="Simple Stock Price Plot",
                output_file="single_dataset_simple_demo.html")
    
    print("\n" + "="*60)
    print("ALL DEMOS COMPLETE!")
    print("="*60)
    print("Generated files:")
    print("1. custom_multi_dataset_demo.html    - Different y configs per dataset")
    print("2. unified_multi_dataset_demo.html   - Same y config for all datasets") 
    print("3. single_dataset_faceted_demo.html  - Single dataset with faceting")
    print("4. single_dataset_simple_demo.html   - Traditional single plot")
    print("\nKey improvements:")
    print("- No more separate 'facets' parameter")
    print("- y can be string, list, or dict")
    print("- Much more intuitive interface")
    print("- Flexible per-dataset configuration")
