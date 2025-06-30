import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.offline import plot
import json
import numpy as np

def superPlotter(data, x="date", y="price", color="quality", filter="location", 
                facet=None, title="Interactive Scatter Plot", output_file="interactive_plot.html"):
    """
    Create an enhanced Plotly scatter plot with custom checkbox filtering and optional faceting.
    Now supports multiple datasets with tabbed interface and dynamic faceting per dataset!
    Each selected filter option creates its own row of subplots.
    
    Parameters:
    - data: pandas DataFrame OR dict of {str: pandas DataFrame} for multiple datasets
    - x: column name for x-axis
    - y: column name for y-axis  
    - color: column name for color grouping
    - filter: column name for checkbox filtering (each selection creates a row)
    - facet: column name for faceting (creates columns within each filter row), optional
    - title: plot title (or base title for multiple datasets)
    - output_file: output HTML filename
    """
    
    # Handle both single DataFrame and dictionary of DataFrames
    if isinstance(data, pd.DataFrame):
        datasets = {"Main": data}
        single_dataset = True
    elif isinstance(data, dict):
        datasets = data
        single_dataset = False
    else:
        raise ValueError("Data must be either a pandas DataFrame or a dictionary of DataFrames")
    
    # Validate all datasets have required columns
    for dataset_name, df in datasets.items():
        required_cols = [x, y, color, filter]
        if facet:
            required_cols.append(facet)
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Dataset '{dataset_name}' missing columns: {missing_cols}")
    
    # Get all unique values across all datasets for consistent color mapping
    all_color_values = set()
    all_filter_values = set()
    
    # Get facet values per dataset
    facet_values_per_dataset = {}
    max_facets = 0
    
    for dataset_name, df in datasets.items():
        all_color_values.update(df[color].unique())
        all_filter_values.update(df[filter].unique())
        
        if facet:
            dataset_facets = sorted(list(df[facet].unique()))
            facet_values_per_dataset[dataset_name] = dataset_facets
            max_facets = max(max_facets, len(dataset_facets))
        else:
            facet_values_per_dataset[dataset_name] = [None]
            max_facets = 1
    
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
    facet_values_per_dataset_json = json.dumps(facet_values_per_dataset)
    
    # Calculate max subplot layout (will be dynamic based on selected filters)
    max_filter_values = len(all_filter_values)
    subplot_cols = max_facets if facet else 1
    max_subplot_rows = max_filter_values  # Each filter can be a row
    
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
        .download-btn {{
            background: #28a745;
            color: white;
            border: none;
            padding: 10px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            margin-bottom: 15px;
            width: 100%;
        }}
        .download-btn:hover {{
            background: #218838;
        }}
        .info-note {{
            font-size: 12px;
            color: #666;
            margin-top: 10px;
            padding: 8px;
            background: #e9ecef;
            border-radius: 4px;
        }}
        #plotDiv {{
            width: 100%;
            height: 600px;
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
                <div class="download-section">
                    <button class="download-btn" onclick="downloadData()">Download Dataset</button>
                </div>
                <div class="filter-section">
                    <div class="filter-title">Filter by {filter.title()}</div>
                    <div class="button-group">
                        <button class="select-all-btn" onclick="selectAll()">Select All</button>
                        <button class="deselect-all-btn" onclick="deselectAll()">Deselect All</button>
                    </div>
                    <div id="filterCheckboxes"></div>
                    <div class="info-note">
                        <strong>Tip:</strong> Each selected filter creates its own row of plots. All facets for a filter appear horizontally in that row.
                    </div>
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
        const yColumn = '{y}';
        const colorColumn = '{color}';
        const facetColumn = {json.dumps(facet) if facet else 'null'};
        const allFilterValues = {json.dumps(all_filter_values)};
        const facetValuesPerDataset = {facet_values_per_dataset_json};
        const singleDataset = {json.dumps(single_dataset)};
        const baseTitle = '{title}';
        
        // Use the consistent color mapping from Python
        const colorMap = {color_mapping_json};
        
        // Current active dataset
        let currentDatasetName = Object.keys(allDatasets)[0];
        let currentData = JSON.parse(allDatasets[currentDatasetName]);
        let currentFacetValues = facetValuesPerDataset[currentDatasetName];
        
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
            currentFacetValues = facetValuesPerDataset[datasetName];
            
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
        
        // Group data by color, filter, and facet value for plotting
        function groupDataByColorFilterAndFacet(data, selectedFilters) {{
            const groups = {{}};
            
            data.forEach(row => {{
                const filterValue = row[filterColumn];
                const colorValue = row[colorColumn];
                const facetValue = facetColumn ? row[facetColumn] : 'main';
                
                // Only include data for selected filters
                if (!selectedFilters.includes(filterValue)) return;
                
                const key = `${{filterValue}}_${{facetValue}}_${{colorValue}}`;
                
                if (!groups[key]) {{
                    groups[key] = {{
                        filterValue: filterValue,
                        colorValue: colorValue,
                        facetValue: facetValue,
                        data: []
                    }};
                }}
                groups[key].data.push(row);
            }});
            
            return groups;
        }}
        
        // Update plot container height dynamically
        function updatePlotHeight(numRows) {{
            const plotDiv = document.getElementById('plotDiv');
            const newHeight = Math.max(500, 350 * numRows);
            plotDiv.style.height = `${{newHeight}}px`;
        }}
        
        // Create plot traces with filter rows and facet columns
        function createPlotTraces(data, selectedFilters) {{
            const groups = groupDataByColorFilterAndFacet(data, selectedFilters);
            const traces = [];
            
            // Calculate layout: each filter is a row, each facet is a column
            const numFilterRows = selectedFilters.length;
            const numFacetCols = currentFacetValues.length;
            
            Object.keys(groups).forEach(key => {{
                const group = groups[key];
                const groupData = group.data;
                
                // Calculate subplot position
                const filterRowIndex = selectedFilters.indexOf(group.filterValue);
                const facetColIndex = currentFacetValues.indexOf(group.facetValue);
                
                let xaxis = 'x';
                let yaxis = 'y';
                
                if (numFilterRows > 1 || numFacetCols > 1) {{
                    // Calculate subplot number (1-indexed)
                    const subplotNum = filterRowIndex * numFacetCols + facetColIndex + 1;
                    
                    if (subplotNum > 1) {{
                        xaxis = `x${{subplotNum}}`;
                        yaxis = `y${{subplotNum}}`;
                    }}
                }}
                
                // Create unique legend group per filter-color combination
                const legendGroup = `${{group.filterValue}}_${{group.colorValue}}`;
                
                // Only show legend for first facet of each filter-color combination
                const showLegend = facetColIndex === 0;
                
                const trace = {{
                    x: groupData.map(row => row[xColumn]),
                    y: groupData.map(row => row[yColumn]),
                    mode: 'markers',
                    type: 'scatter',
                    name: `${{group.filterValue}} - ${{group.colorValue}}`,
                    legendgroup: legendGroup,
                    showlegend: showLegend,
                    xaxis: xaxis,
                    yaxis: yaxis,
                    marker: {{
                        color: colorMap[group.colorValue],
                        size: 8,
                        line: {{
                            width: 1,
                            color: 'rgba(0,0,0,0.2)'
                        }}
                    }},
                    hovertemplate: `<b>${{group.colorValue}}</b><br>` +
                                  `{x}: %{{x}}<br>` +
                                  `{y}: %{{y}}<br>` +
                                  `{filter}: %{{customdata[0]}}<br>` +
                                  (facetColumn ? `{facet}: %{{customdata[1]}}<br>` : '') +
                                  '<extra></extra>',
                    customdata: groupData.map(row => facetColumn ? 
                        [row[filterColumn], row[facetColumn]] : [row[filterColumn]])
                }};
                traces.push(trace);
            }});
            
            return traces;
        }}
        
        // Download data functionality
        function downloadData() {{
            const currentDatasetData = currentData;
            const datasetName = currentDatasetName;
            
            // Convert to CSV
            if (currentDatasetData.length === 0) {{
                alert('No data available to download');
                return;
            }}
            
            const headers = Object.keys(currentDatasetData[0]);
            const csvContent = [
                headers.join(','),
                ...currentDatasetData.map(row => 
                    headers.map(header => {{
                        const value = row[header];
                        // Handle values that might contain commas or quotes
                        if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {{
                            return `"${{value.replace(/"/g, '""')}}"`;
                        }}
                        return value;
                    }}).join(',')
                )
            ].join('\\n');
            
            // Create and trigger download
            const blob = new Blob([csvContent], {{ type: 'text/csv;charset=utf-8;' }});
            const link = document.createElement('a');
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', `${{datasetName}}_data.csv`);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
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
            
            if (selectedFilters.length === 0) {{
                // Clear plot if no filters selected
                updatePlotHeight(1);
                Plotly.newPlot('plotDiv', [], {{title: 'Select at least one filter option'}});
                return;
            }}
            
            // Calculate number of rows for height adjustment
            const numFilterRows = selectedFilters.length;
            updatePlotHeight(numFilterRows);
            
            // Create new traces
            const traces = createPlotTraces(currentData, selectedFilters);
            
            // Create dynamic title
            const plotTitle = singleDataset ? baseTitle : `${{baseTitle}} - ${{currentDatasetName}}`;
            
            // Calculate subplot layout
            const numFacetCols = currentFacetValues.length;
            
            // Create layout with subplots
            let layout = {{
                title: plotTitle,
                hovermode: 'closest',
                showlegend: true,
                height: Math.max(400, 300 * numFilterRows)
            }};
            
            if (numFilterRows > 1 || numFacetCols > 1) {{
                // Create subplot specifications
                const subplotSpecs = [];
                for (let row = 0; row < numFilterRows; row++) {{
                    const rowSpecs = [];
                    for (let col = 0; col < numFacetCols; col++) {{
                        rowSpecs.push({{}});
                    }}
                    subplotSpecs.push(rowSpecs);
                }}
                
                layout.grid = {{
                    rows: numFilterRows,
                    columns: numFacetCols,
                    pattern: 'independent',
                    roworder: 'top to bottom'
                }};
                
                // Add axis labels and titles for each subplot
                let subplotCounter = 1;
                for (let filterIdx = 0; filterIdx < selectedFilters.length; filterIdx++) {{
                    const filterValue = selectedFilters[filterIdx];
                    
                    for (let facetIdx = 0; facetIdx < currentFacetValues.length; facetIdx++) {{
                        const facetValue = currentFacetValues[facetIdx];
                        
                        let xaxisKey = subplotCounter === 1 ? 'xaxis' : `xaxis${{subplotCounter}}`;
                        let yaxisKey = subplotCounter === 1 ? 'yaxis' : `yaxis${{subplotCounter}}`;
                        
                        layout[xaxisKey] = {{
                            title: filterIdx === selectedFilters.length - 1 ? '{x}' : '',
                            anchor: yaxisKey.replace('yaxis', 'y')
                        }};
                        layout[yaxisKey] = {{
                            title: facetIdx === 0 ? '{y}' : '',
                            anchor: xaxisKey.replace('xaxis', 'x')
                        }};
                        
                        // Add subplot titles
                        if (!layout.annotations) layout.annotations = [];
                        
                        // Filter title (left side of row)
                        if (facetIdx === 0) {{
                            layout.annotations.push({{
                                text: `<b>{filter}: ${{filterValue}}</b>`,
                                showarrow: false,
                                x: -0.02,
                                y: 1 - (filterIdx + 0.5) / numFilterRows,
                                xref: 'paper',
                                yref: 'paper',
                                xanchor: 'right',
                                yanchor: 'middle',
                                font: {{ size: 12, color: '#333' }},
                                textangle: -90
                            }});
                        }}
                        
                        // Facet title (top of column)
                        if (facetColumn && filterIdx === 0) {{
                            layout.annotations.push({{
                                text: `{facet or 'Facet'}: ${{facetValue}}`,
                                showarrow: false,
                                x: (facetIdx + 0.5) / numFacetCols,
                                y: 1.02,
                                xref: 'paper',
                                yref: 'paper',
                                xanchor: 'center',
                                yanchor: 'bottom',
                                font: {{ size: 12, color: '#333' }}
                            }});
                        }}
                        
                        subplotCounter++;
                    }}
                }}
            }} else {{
                layout.xaxis = {{ title: '{x}' }};
                layout.yaxis = {{ title: '{y}' }};
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
    # Create sample data for multiple datasets
    np.random.seed(42)
    
    # Dataset 1: Stock prices (has Tech and Finance categories)
    dates1 = pd.date_range('2023-01-01', periods=100)
    stock_data = {
        'date': dates1,
        'price': np.random.normal(100, 15, 100) + np.random.normal(0, 3, 100).cumsum(),
        'quality': np.random.choice(['High', 'Medium', 'Low'], 100),
        'location': np.random.choice(['New York', 'London', 'Tokyo'], 100),
        'category': np.random.choice(['Tech', 'Finance'], 100)
    }
    
    # Dataset 2: Crypto prices (has Tech, Finance, and DeFi categories)
    dates2 = pd.date_range('2023-01-01', periods=120)
    crypto_data = {
        'date': dates2,
        'price': np.random.normal(50, 20, 120) + np.random.normal(0, 8, 120).cumsum(),
        'quality': np.random.choice(['High', 'Medium', 'Low'], 120),
        'location': np.random.choice(['New York', 'London', 'Tokyo', 'Seoul'], 120),
        'category': np.random.choice(['Tech', 'Finance', 'DeFi'], 120)
    }
    
    # Dataset 3: Commodity prices (has only Energy and Metals categories)
    dates3 = pd.date_range('2023-01-01', periods=80)
    commodity_data = {
        'date': dates3,
        'price': np.random.normal(200, 25, 80) + np.random.normal(0, 4, 80).cumsum(),
        'quality': np.random.choice(['High', 'Medium', 'Low'], 80),
        'location': np.random.choice(['New York', 'London', 'Singapore'], 80),
        'category': np.random.choice(['Energy', 'Metals'], 80)  # Different categories!
    }
    
    # Create DataFrames
    datasets = {
        'Stocks': pd.DataFrame(stock_data),
        'Crypto': pd.DataFrame(crypto_data),
        'Commodities': pd.DataFrame(commodity_data)
    }
    
    # Create multi-dataset plot with filter rows and facet columns
    superPlotter(datasets, 
                x="date", 
                y="price", 
                color="quality", 
                filter="location",
                facet="category",
                title="Market Analysis Dashboard",
                output_file="filter_rows_demo.html")
    
    print("Filter rows demo complete! Open 'filter_rows_demo.html' in your browser.")
    print("Now each selected filter creates its own row:")
    print("- Select New York + London = 2 rows")
    print("- Each row shows all facets (categories) horizontally")
    print("- Legend groups by filter-color combination")
    
    # Also create a single dataset example for comparison
    superPlotter(datasets['Stocks'], 
                x="date", 
                y="price", 
                color="quality", 
                filter="location",
                facet="category",
                title="Single Dataset - Filter Rows",
                output_file="single_filter_rows_demo.html")
    
    print("Single dataset demo complete! Open 'single_filter_rows_demo.html' in your browser.")
