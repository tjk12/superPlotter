import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.offline import plot
import json
import numpy as np

def superPlotter(data, x="date", y="price", color="quality", filter="location", 
                title="Interactive Line Plot", output_file="interactive_plot.html",
                filter_descriptions=None):
    """
    Create an enhanced Plotly line plot with custom checkbox filtering, multiple y-axis support,
    and interactive data tables with pivot functionality and column-specific aggregation.
    Now supports multiple datasets with tabbed interface and dynamic y-axis plotting per dataset!
    Each selected filter option creates its own row of subplots.
    
    Parameters:
    - data: pandas DataFrame OR dict of {str: pandas DataFrame} for multiple datasets
    - x: column name for x-axis
    - y: column name for y-axis OR list of column names OR dict of {dataset_name: list of column names}
    - color: column name for color grouping
    - filter: column name for checkbox filtering (each selection creates a row)
    - title: plot title (or base title for multiple datasets)
    - output_file: output HTML filename
    - filter_descriptions: dict mapping filter values to descriptions (e.g., {'London': 'Financial Hub of Europe'})
    """
    
    # Default filter descriptions
    default_descriptions = {
        'London': 'Financial Hub of Europe',
        'New York': 'Wall Street Financial Center',
        'Seoul': 'Asian Technology Capital',
        'Tokyo': 'Major Asian Financial Market'
    }
    
    # Merge with user-provided descriptions
    if filter_descriptions is None:
        filter_descriptions = default_descriptions
    else:
        # Combine defaults with user descriptions, user descriptions take priority
        combined_descriptions = default_descriptions.copy()
        combined_descriptions.update(filter_descriptions)
        filter_descriptions = combined_descriptions
    
    # Handle both single DataFrame and dictionary of DataFrames
    if isinstance(data, pd.DataFrame):
        datasets = {"Main": data}
        single_dataset = True
    elif isinstance(data, dict):
        datasets = data
        single_dataset = False
    else:
        raise ValueError("Data must be either a pandas DataFrame or a dictionary of DataFrames")
    
    # Handle y parameter - can be string, list, or dict
    y_columns_per_dataset = {}
    
    if isinstance(y, str):
        # Single y column for all datasets
        for dataset_name in datasets.keys():
            y_columns_per_dataset[dataset_name] = [y]
    elif isinstance(y, list):
        # Same list of y columns for all datasets
        for dataset_name in datasets.keys():
            y_columns_per_dataset[dataset_name] = y
    elif isinstance(y, dict):
        # Different y columns per dataset - must match dataset keys
        if not isinstance(data, dict):
            raise ValueError("If y is a dictionary, data must also be a dictionary")
        if set(y.keys()) != set(data.keys()):
            raise ValueError("Keys in y dictionary must match keys in data dictionary")
        for dataset_name, y_cols in y.items():
            if not isinstance(y_cols, list):
                raise ValueError(f"y values must be lists, got {type(y_cols)} for dataset '{dataset_name}'")
            y_columns_per_dataset[dataset_name] = y_cols
    else:
        raise ValueError("y must be a string, list, or dictionary")
    
    # Validate all datasets have required columns
    for dataset_name, df in datasets.items():
        required_cols = [x, color, filter]
        required_cols.extend(y_columns_per_dataset[dataset_name])
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Dataset '{dataset_name}' missing columns: {missing_cols}")
    
    # Get all unique values across all datasets for consistent color mapping
    all_color_values = set()
    all_filter_values = set()
    
    # Get y columns per dataset and calculate max y columns
    max_y_columns = 0
    
    for dataset_name, df in datasets.items():
        all_color_values.update(df[color].unique())
        all_filter_values.update(df[filter].unique())
        max_y_columns = max(max_y_columns, len(y_columns_per_dataset[dataset_name]))
    
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
        # Convert date columns to ISO format strings for better JavaScript handling
        df_copy = df.copy()
        if df_copy[x].dtype.name.startswith('datetime'):
            df_copy[x] = df_copy[x].dt.strftime('%Y-%m-%d')
        datasets_json[dataset_name] = df_copy.to_json(orient='records')
    
    color_mapping_json = json.dumps(color_mapping)
    y_columns_per_dataset_json = json.dumps(y_columns_per_dataset)
    filter_descriptions_json = json.dumps(filter_descriptions)
    
    # Calculate max subplot layout (will be dynamic based on selected filters)
    max_filter_values = len(all_filter_values)
    subplot_cols = max_y_columns
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
        .view-tabs {{
            display: flex;
            background: #f8f9fa;
            border-radius: 8px;
            padding: 4px;
            margin-bottom: 20px;
        }}
        .view-tab {{
            background: transparent;
            border: none;
            padding: 8px 16px;
            cursor: pointer;
            font-size: 14px;
            border-radius: 4px;
            transition: all 0.3s ease;
            color: #666;
        }}
        .view-tab.active {{
            background: white;
            color: #007bff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
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
            max-width: 300px;
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
            flex-direction: column;
            gap: 4px;
        }}
        .checkbox-row {{
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
            color: #333;
            font-weight: 500;
        }}
        .checkbox-description {{
            font-size: 12px;
            color: #666;
            margin-left: 24px;
            font-style: italic;
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
        
        /* Data Table Styles */
        .table-container {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .pivot-controls {{
            padding: 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #e0e0e0;
        }}
        .control-group {{
            margin-bottom: 15px;
        }}
        .control-label {{
            font-size: 14px;
            font-weight: 500;
            margin-bottom: 5px;
            display: block;
            color: #333;
        }}
        .control-select {{
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            background: white;
        }}
        .control-row {{
            display: flex;
            gap: 15px;
            align-items: end;
        }}
        .control-column {{
            flex: 1;
        }}
        .apply-btn {{
            background: #007bff;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            white-space: nowrap;
        }}
        .apply-btn:hover {{
            background: #0056b3;
        }}
        .table-wrapper {{
            max-height: 600px;
            overflow: auto;
            padding: 20px;
        }}
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        .data-table th,
        .data-table td {{
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }}
        .data-table th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #333;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        .data-table tbody tr:hover {{
            background: #f8f9fa;
        }}
        .numeric-cell {{
            text-align: right;
            font-family: 'Consolas', 'Monaco', monospace;
        }}
        .table-stats {{
            padding: 15px 20px;
            background: #f8f9fa;
            border-top: 1px solid #e0e0e0;
            font-size: 12px;
            color: #666;
        }}
        .view-content {{
            display: none;
        }}
        .view-content.active {{
            display: block;
        }}
        
        /* NEW: Column-specific aggregation styles */
        .column-aggregation-container {{
            background: #f1f3f4;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
        }}
        .column-aggregation-title {{
            font-weight: 600;
            color: #333;
            margin-bottom: 10px;
            font-size: 14px;
        }}
        .column-agg-row {{
            display: flex;
            align-items: center;
            margin-bottom: 8px;
            gap: 10px;
        }}
        .column-name {{
            font-weight: 500;
            color: #555;
            min-width: 120px;
            font-size: 13px;
        }}
        .column-agg-select {{
            flex: 1;
            padding: 6px 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 12px;
            background: white;
        }}
        .reset-agg-btn {{
            background: #ffc107;
            color: #212529;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            margin-left: 10px;
        }}
        .reset-agg-btn:hover {{
            background: #e0a800;
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
                        <strong>Tip:</strong> Each selected filter creates its own row of plots. All y-variables for a filter appear horizontally in that row.
                    </div>
                </div>
            </div>
            <div class="plot-container">
                <!-- View toggle buttons -->
                <div class="view-tabs">
                    <button class="view-tab active" data-view="plot" onclick="switchView('plot')">Charts</button>
                    <button class="view-tab" data-view="table" onclick="switchView('table')">Data Table</button>
                </div>
                
                <!-- Plot view -->
                <div id="plotView" class="view-content active">
                    <div id="plotDiv"></div>
                </div>
                
                <!-- Table view -->
                <div id="tableView" class="view-content">
                    <div class="table-container">
                        <div class="pivot-controls">
                            <div class="control-row">
                                <div class="control-column">
                                    <label class="control-label">Group By (Hold Ctrl for multiple)</label>
                                    <select id="groupBySelect" class="control-select" multiple style="height: 80px;">
                                        <option value="">No Grouping</option>
                                    </select>
                                </div>
                                <div class="control-column">
                                    <button class="apply-btn" onclick="updateTable()" style="height: 80px;">Apply Grouping & Aggregation</button>
                                </div>
                            </div>
                            <div id="aggregationControls" style="margin-top: 15px; display: none;">
                                <div class="control-label">Column-Specific Aggregation Functions</div>
                                <div id="columnAggregationContainer" style="max-height: 200px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; border-radius: 4px; background: #f9f9f9;">
                                </div>
                            </div>
                        </div>
                        <div class="table-wrapper">
                            <table class="data-table" id="dataTable">
                                <thead id="tableHead"></thead>
                                <tbody id="tableBody"></tbody>
                            </table>
                        </div>
                        <div class="table-stats" id="tableStats"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Data from Python
        const allDatasets = {json.dumps(datasets_json)};
        const filterColumn = '{filter}';
        const xColumn = '{x}';
        const yColumnsPerDataset = {y_columns_per_dataset_json};
        const colorColumn = '{color}';
        const allFilterValues = {json.dumps(all_filter_values)};
        const singleDataset = {json.dumps(single_dataset)};
        const baseTitle = '{title}';
        const filterDescriptions = {filter_descriptions_json};
        
        // Use the consistent color mapping from Python
        const colorMap = {color_mapping_json};
        
        // Current active dataset
        let currentDatasetName = Object.keys(allDatasets)[0];
        let currentData = JSON.parse(allDatasets[currentDatasetName]);
        let currentYColumns = yColumnsPerDataset[currentDatasetName];
        let currentView = 'plot';
        
        // NEW: Column-specific aggregation settings
        let columnAggregations = {{}};
        
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
            currentYColumns = yColumnsPerDataset[datasetName];
            
            // Reset column aggregations for new dataset
            columnAggregations = {{}};
            
            // Update filter checkboxes based on current dataset
            updateFilterCheckboxes();
            
            // Update group by options for new dataset
            updateGroupByOptions();
            
            // Update column aggregation controls
            updateColumnAggregationControls();
            
            // Immediately update both views
            updatePlot();
            updateTable();
        }}
        
        // Switch between views
        function switchView(viewName) {{
            currentView = viewName;
            
            // Update view tab buttons using data attributes
            document.querySelectorAll('.view-tab').forEach(tab => {{
                tab.classList.remove('active');
                if (tab.dataset.view === viewName) {{
                    tab.classList.add('active');
                }}
            }});
            
            // Update view content
            document.querySelectorAll('.view-content').forEach(content => {{
                content.classList.remove('active');
            }});
            
            const targetView = document.getElementById(viewName + 'View');
            if (targetView) {{
                targetView.classList.add('active');
            }}
            
            // Update the appropriate view
            if (viewName === 'plot') {{
                updatePlot();
            }} else if (viewName === 'table') {{
                updateTable();
            }}
        }}
        
        // NEW: Update column aggregation controls
        function updateColumnAggregationControls() {{
            const container = document.getElementById('columnAggregationControls');
            container.innerHTML = '';
            
            if (currentData.length === 0) return;
            
            // Get all numeric columns
            const allColumns = Object.keys(currentData[0]);
            const numericColumns = allColumns.filter(col => {{
                const sampleValues = currentData.slice(0, 10).map(row => row[col]);
                return sampleValues.some(val => 
                    val !== null && val !== undefined && val !== '' && 
                    !isNaN(parseFloat(val)) && isFinite(val)
                );
            }});
            
            // Create controls for each numeric column
            numericColumns.forEach(col => {{
                const row = document.createElement('div');
                row.className = 'column-agg-row';
                
                const label = document.createElement('div');
                label.className = 'column-name';
                label.textContent = col;
                
                const select = document.createElement('select');
                select.className = 'column-agg-select';
                select.id = `agg_${{col}}`;
                
                // Add options
                const options = [
                    {{value: '', text: 'Use Default'}},
                    {{value: 'sum', text: 'Sum'}},
                    {{value: 'mean', text: 'Average'}},
                    {{value: 'count', text: 'Count'}},
                    {{value: 'min', text: 'Minimum'}},
                    {{value: 'max', text: 'Maximum'}},
                    {{value: 'first', text: 'First Value'}},
                    {{value: 'last', text: 'Last Value'}}
                ];
                
                options.forEach(opt => {{
                    const option = document.createElement('option');
                    option.value = opt.value;
                    option.textContent = opt.text;
                    select.appendChild(option);
                }});
                
                // Set current value if exists
                if (columnAggregations[col]) {{
                    select.value = columnAggregations[col];
                }}
                
                // Add change handler
                select.addEventListener('change', () => {{
                    if (select.value === '') {{
                        delete columnAggregations[col];
                    }} else {{
                        columnAggregations[col] = select.value;
                    }}
                }});
                
                row.appendChild(label);
                row.appendChild(select);
                container.appendChild(row);
            }});
        }}
        
        // NEW: Reset column aggregations
        function resetColumnAggregations() {{
            columnAggregations = {{}};
            updateColumnAggregationControls();
        }}

        // ENHANCED: Add year extraction to filtered data
        function getFilteredDataWithYear() {{
            const filteredData = getFilteredData();
            
            // Add year column to each row if it doesn't exist
            return filteredData.map(row => {{
                const newRow = {{ ...row }};
                if (!newRow.Year && row[xColumn]) {{
                    newRow.Year = extractYear(row[xColumn]);
                }}
                return newRow;
            }});
        }}

        // ENHANCED: Extract year from date values
        function extractYear(dateValue) {{
            if (!dateValue) return null;
            
            let date;
            
            // Handle different date formats
            if (typeof dateValue === 'string') {{
                // Try parsing common date formats
                if (dateValue.match(/^\d{{4}}-\d{{2}}-\d{{2}}/)) {{
                    // YYYY-MM-DD format
                    date = new Date(dateValue);
                }} else if (dateValue.match(/^\d{{2}}\/\d{{2}}\/\d{{4}}/)) {{
                    // MM/DD/YYYY format
                    date = new Date(dateValue);
                }} else if (dateValue.match(/^\d{{4}}/)) {{
                    // Just year
                    return parseInt(dateValue.substring(0, 4));
                }} else {{
                    date = new Date(dateValue);
                }}
            }} else if (dateValue instanceof Date) {{
                date = dateValue;
            }} else {{
                // Try to convert to date
                date = new Date(dateValue);
            }}
            
            // Check if date is valid
            if (isNaN(date.getTime())) {{
                console.warn('Invalid date value:', dateValue);
                return null;
            }}
            
            return date.getFullYear();
        }}


        // Updated updateAggregationControls to only show numeric columns
        function updateAggregationControls() {{
            const groupBySelect = document.getElementById('groupBySelect');
            const aggregationControls = document.getElementById('aggregationControls');
            const container = document.getElementById('columnAggregationContainer');
            
            const selectedGroupColumns = Array.from(groupBySelect.selectedOptions).map(option => option.value);
            
            if (selectedGroupColumns.length === 0) {{
                aggregationControls.style.display = 'none';
                return;
            }}
            
            aggregationControls.style.display = 'block';
            container.innerHTML = '';
            
            // Get only numeric columns that are not grouping columns
            if (currentData.length > 0) {{
                const numericColumns = getNumericColumns(currentData);
                const nonGroupingNumericColumns = numericColumns.filter(col => !selectedGroupColumns.includes(col));
                
                nonGroupingNumericColumns.forEach(col => {{
                    const controlDiv = document.createElement('div');
                    controlDiv.style.cssText = 'margin-bottom: 10px; display: flex; align-items: center; gap: 10px;';
                    
                    const label = document.createElement('label');
                    label.textContent = col;
                    label.style.cssText = 'min-width: 120px; font-weight: 500;';
                    
                    const select = document.createElement('select');
                    select.id = `agg_${{col}}`;
                    select.className = 'control-select';
                    select.style.cssText = 'flex: 1; max-width: 150px;';
                    
                    // Add numeric aggregation options only
                    const numericOptions = [
                        {{value: 'sum', text: 'Sum'}},
                        {{value: 'mean', text: 'Average'}},
                        {{value: 'count', text: 'Count'}},
                        {{value: 'min', text: 'Minimum'}},
                        {{value: 'max', text: 'Maximum'}},
                        {{value: 'first', text: 'First Value'}},
                        {{value: 'last', text: 'Last Value'}}
                    ];
                    
                    numericOptions.forEach(opt => {{
                        const option = document.createElement('option');
                        option.value = opt.value;
                        option.textContent = opt.text;
                        if (opt.value === 'sum') option.selected = true; // Default for numeric
                        select.appendChild(option);
                    }});
                    
                    const typeLabel = document.createElement('span');
                    typeLabel.textContent = '(numeric)';
                    typeLabel.style.cssText = 'font-size: 11px; color: #666; font-style: italic;';
                    
                    controlDiv.appendChild(label);
                    controlDiv.appendChild(select);
                    controlDiv.appendChild(typeLabel);
                    container.appendChild(controlDiv);
                }});
            }}
        }}

        // Replace the updateGroupByOptions function
        function updateGroupByOptions() {{
            const groupBySelect = document.getElementById('groupBySelect');
            groupBySelect.innerHTML = '';
            
            // Get all column names from current dataset
            if (currentData.length > 0) {{
                const columns = Object.keys(currentData[0]);
                
                // Add regular columns
                columns.forEach(col => {{
                    const option = document.createElement('option');
                    option.value = col;
                    option.textContent = col;
                    groupBySelect.appendChild(option);
                }});
                
                // Add Year option if date column exists
                if (columns.includes(xColumn)) {{
                    const yearOption = document.createElement('option');
                    yearOption.value = 'Year';
                    yearOption.textContent = 'Year (from date)';
                    groupBySelect.appendChild(yearOption);
                }}
            }}
            
            // Add event listener for multi-select changes
            groupBySelect.addEventListener('change', function() {{
                updateAggregationControls();
            }});
        }}
        
        // Get filtered data based on current filter selections
        function getFilteredData() {{
            const selectedFilters = [];
            const currentFilterValues = [...new Set(currentData.map(row => row[filterColumn]))].sort();
            
            currentFilterValues.forEach(value => {{
                const checkbox = document.getElementById(`filter_${{value}}`);
                if (checkbox && checkbox.checked) {{
                    selectedFilters.push(value);
                }}
            }});
            
            if (selectedFilters.length === 0) {{
                return [];
            }}
            
            return currentData.filter(row => selectedFilters.includes(row[filterColumn]));
        }}
                



        // Updated helper function to identify numeric columns only
        function getNumericColumns(data) {{
            if (!data || data.length === 0) return [];
            
            const allColumns = Object.keys(data[0]);
            return allColumns.filter(col => {{
                const sampleValues = data.slice(0, 100).map(row => row[col])
                    .filter(val => val !== null && val !== undefined && val !== '');
                
                // Check if at least 80% of non-null values are numeric
                if (sampleValues.length === 0) return false;
                
                const numericCount = sampleValues.filter(val => 
                    !isNaN(parseFloat(val)) && isFinite(val)
                ).length;
                
                return (numericCount / sampleValues.length) >= 0.8;
            }});
        }}

        // Updated updateTable function to only show numeric columns
        function updateTable() {{
            const filteredData = getFilteredDataWithYear();
            const groupBySelect = document.getElementById('groupBySelect');
            const selectedGroupColumns = Array.from(groupBySelect.selectedOptions).map(option => option.value);
            
            const tableHead = document.getElementById('tableHead');
            const tableBody = document.getElementById('tableBody');
            const tableStats = document.getElementById('tableStats');
            
            if (filteredData.length === 0) {{
                tableHead.innerHTML = '';
                tableBody.innerHTML = '<tr><td colspan="100%" style="text-align: center; padding: 20px; color: #666;">No data to display. Please select at least one filter option.</td></tr>';
                tableStats.innerHTML = '';
                return;
            }}
            
            let tableData = [...filteredData];
            
            // Get numeric columns only, plus grouping columns
            const numericColumns = getNumericColumns(tableData);
            const allColumns = Object.keys(tableData[0]);
            
            // Include grouping columns even if they're not numeric
            let displayColumns = [...new Set([...selectedGroupColumns, ...numericColumns])];
            
            // Apply grouping and aggregation if specified
            if (selectedGroupColumns.length > 0) {{
                try {{
                    // Get column-specific aggregation functions
                    const columnAggregations = {{}};
                    numericColumns.forEach(col => {{
                        if (!selectedGroupColumns.includes(col)) {{
                            const selectElement = document.getElementById(`agg_${{col}}`);
                            if (selectElement) {{
                                columnAggregations[col] = selectElement.value;
                            }}
                        }}
                    }});
                    
                    tableData = performAggregation(filteredData, selectedGroupColumns, columnAggregations);
                    if (tableData.length > 0) {{
                        // After aggregation, still only show numeric + grouping columns
                        const aggregatedNumericColumns = getNumericColumns(tableData);
                        displayColumns = [...new Set([...selectedGroupColumns, ...aggregatedNumericColumns])];
                    }}
                }} catch (error) {{
                    console.error('Error in aggregation:', error);
                    tableBody.innerHTML = '<tr><td colspan="100%" style="text-align: center; padding: 20px; color: #d32f2f;">Error performing aggregation. Please try different settings.</td></tr>';
                    return;
                }}
            }}
            
            // Filter tableData to only include display columns
            tableData = tableData.map(row => {{
                const filteredRow = {{}};
                displayColumns.forEach(col => {{
                    filteredRow[col] = row[col];
                }});
                return filteredRow;
            }});
            
            // Create table header
            const headerRow = document.createElement('tr');
            displayColumns.forEach(col => {{
                const th = document.createElement('th');
                th.textContent = col;
                th.style.cursor = 'pointer';
                th.title = 'Click to sort';
                th.onclick = () => sortTable(col);
                headerRow.appendChild(th);
            }});
            tableHead.innerHTML = '';
            tableHead.appendChild(headerRow);
            
            // Create table body
            tableBody.innerHTML = '';
            
            tableData.forEach((row, index) => {{
                const tr = document.createElement('tr');
                displayColumns.forEach(col => {{
                    const td = document.createElement('td');
                    const value = row[col];
                    
                    // Format values based on type
                    if (value === null || value === undefined) {{
                        td.textContent = '';
                    }} else if (typeof value === 'number') {{
                        td.className = 'numeric-cell';
                        if (Number.isInteger(value)) {{
                            td.textContent = value.toLocaleString();
                        }} else {{
                            td.textContent = value.toLocaleString(undefined, {{
                                minimumFractionDigits: 0,
                                maximumFractionDigits: 3
                            }});
                        }}
                    }} else {{
                        td.textContent = String(value);
                    }}
                    
                    tr.appendChild(td);
                }});
                tableBody.appendChild(tr);
            }});
            
            // Update table stats
            let statsText = `Showing ${{tableData.length}} rows (numeric columns only)`;
            if (selectedGroupColumns.length > 0) {{
                const groupLabels = selectedGroupColumns.map(col => 
                    col === 'Year' ? 'Year (from date)' : col
                );
                statsText += ` (grouped by: ${{groupLabels.join(', ')}})`;
            }}
            if (filteredData.length !== currentData.length) {{
                statsText += ` of ${{currentData.length}} total records`;
            }}
            tableStats.innerHTML = statsText;
        }}





        // Updated performAggregation to handle only numeric columns for aggregation
        function performAggregation(data, groupByColumns, columnAggregations) {{
            if (!groupByColumns || groupByColumns.length === 0) {{
                return data;
            }}
            
            // If grouping by Year, ensure Year column exists in data
            let processedData = data;
            if (groupByColumns.includes('Year')) {{
                processedData = data.map(row => {{
                    const newRow = {{ ...row }};
                    if (!newRow.Year && row[xColumn]) {{
                        newRow.Year = extractYear(row[xColumn]);
                    }}
                    return newRow;
                }});
            }}
            
            // Group data by the groupBy columns
            const groups = {{}};
            processedData.forEach(row => {{
                // Create composite key from all grouping columns
                const keyParts = groupByColumns.map(col => {{
                    let value = row[col];
                    
                    // Handle null/undefined years
                    if (col === 'Year' && (value === null || value === undefined)) {{
                        value = 'Unknown Year';
                    }}
                    
                    return String(value || 'null');
                }});
                
                const key = keyParts.join('|||'); // Use separator that won't appear in data
                
                if (!groups[key]) {{
                    groups[key] = {{
                        keyValues: keyParts,
                        rows: []
                    }};
                }}
                groups[key].rows.push(row);
            }});
            
            // Aggregate each group
            const aggregated = [];
            
            // Sort groups by their key values
            const sortedGroupKeys = Object.keys(groups).sort((a, b) => {{
                const groupA = groups[a].keyValues;
                const groupB = groups[b].keyValues;
                
                // Compare each key part
                for (let i = 0; i < Math.min(groupA.length, groupB.length); i++) {{
                    const col = groupByColumns[i];
                    let valA = groupA[i];
                    let valB = groupB[i];
                    
                    // Special handling for Year sorting
                    if (col === 'Year') {{
                        const yearA = valA === 'Unknown Year' ? Infinity : parseInt(valA);
                        const yearB = valB === 'Unknown Year' ? Infinity : parseInt(valB);
                        if (yearA !== yearB) return yearA - yearB;
                    }} else {{
                        const comparison = valA.localeCompare(valB);
                        if (comparison !== 0) return comparison;
                    }}
                }}
                return 0;
            }});
            
            sortedGroupKeys.forEach(key => {{
                const group = groups[key];
                const aggregatedRow = {{}};
                
                // Set the grouping column values
                groupByColumns.forEach((col, index) => {{
                    const value = group.keyValues[index];
                    if (col === 'Year' && value !== 'Unknown Year') {{
                        aggregatedRow[col] = parseInt(value);
                    }} else {{
                        aggregatedRow[col] = value === 'null' ? null : value;
                    }}
                }});
                
                // Get only numeric columns from the first row for aggregation
                const numericColumns = getNumericColumns(group.rows);
                
                numericColumns.forEach(col => {{
                    if (groupByColumns.includes(col)) return; // Skip the grouping columns
                    
                    // Get aggregation function for this column
                    const aggFunc = columnAggregations[col] || 'sum'; // Default to sum for numeric
                    
                    // Get all values for this column in the group
                    const allValues = group.rows.map(row => row[col]);
                    const numericValues = allValues.filter(val => {{
                        return val !== null && val !== undefined && val !== '' && 
                            !isNaN(parseFloat(val)) && isFinite(val);
                    }}).map(val => parseFloat(val));
                    
                    // Apply aggregation function (all numeric)
                    switch (aggFunc) {{
                        case 'sum':
                            aggregatedRow[col] = numericValues.length > 0 ? 
                                numericValues.reduce((a, b) => a + b, 0) : null;
                            break;
                        case 'mean':
                            aggregatedRow[col] = numericValues.length > 0 ? 
                                numericValues.reduce((a, b) => a + b, 0) / numericValues.length : null;
                            break;
                        case 'count':
                            aggregatedRow[col] = numericValues.length;
                            break;
                        case 'min':
                            aggregatedRow[col] = numericValues.length > 0 ? 
                                Math.min(...numericValues) : null;
                            break;
                        case 'max':
                            aggregatedRow[col] = numericValues.length > 0 ? 
                                Math.max(...numericValues) : null;
                            break;
                        case 'first':
                            aggregatedRow[col] = numericValues.length > 0 ? numericValues[0] : null;
                            break;
                        case 'last':
                            aggregatedRow[col] = numericValues.length > 0 ? 
                                numericValues[numericValues.length - 1] : null;
                            break;
                        default:
                            aggregatedRow[col] = numericValues.length > 0 ? numericValues[0] : null;
                    }}
                }});
                
                aggregated.push(aggregatedRow);
            }});
            
            return aggregated;
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
                
                // Create checkbox row
                const checkboxRow = document.createElement('div');
                checkboxRow.className = 'checkbox-row';
                
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.id = `filter_${{value}}`;
                checkbox.value = value;
                checkbox.checked = true;
                checkbox.addEventListener('change', () => {{
                    if (currentView === 'plot') {{
                        updatePlot();
                    }} else {{
                        updateTable();
                    }}
                }});
                
                const label = document.createElement('label');
                label.htmlFor = `filter_${{value}}`;
                label.textContent = value;
                
                checkboxRow.appendChild(checkbox);
                checkboxRow.appendChild(label);
                div.appendChild(checkboxRow);
                
                // Add description if available
                if (filterDescriptions[value]) {{
                    const description = document.createElement('div');
                    description.className = 'checkbox-description';
                    description.textContent = filterDescriptions[value];
                    div.appendChild(description);
                }}
                
                container.appendChild(div);
            }});
        }}
        
        // Group data by color, filter, and y column for plotting
        function groupDataByColorFilterAndY(data, selectedFilters) {{
            const groups = {{}};
            
            data.forEach(row => {{
                const filterValue = row[filterColumn];
                const colorValue = row[colorColumn];
                
                // Only include data for selected filters
                if (!selectedFilters.includes(filterValue)) return;
                
                // Create groups for each y column
                currentYColumns.forEach(yCol => {{
                    const key = `${{filterValue}}_${{yCol}}_${{colorValue}}`;
                    
                    if (!groups[key]) {{
                        groups[key] = {{
                            filterValue: filterValue,
                            colorValue: colorValue,
                            yColumn: yCol,
                            data: []
                        }};
                    }}
                    groups[key].data.push(row);
                }});
            }});
            
            return groups;
        }}
        
        // Update plot container height dynamically
        function updatePlotHeight(numRows) {{
            const plotDiv = document.getElementById('plotDiv');
            const newHeight = Math.max(500, 350 * numRows);
            plotDiv.style.height = `${{newHeight}}px`;
        }}
        
        // Parse date string for proper axis formatting
        function parseDate(dateStr) {{
            return new Date(dateStr);
        }}
        
        // FIXED: This is the corrected createPlotTraces function and layout section
        function createPlotTraces(data, selectedFilters) {{
            const groups = groupDataByColorFilterAndY(data, selectedFilters);
            const traces = [];
            
            // Calculate layout: each filter is a row, each y column is a column
            const numFilterRows = selectedFilters.length;
            const numYCols = currentYColumns.length;
            
            const sortedGroupKeys = Object.keys(groups).sort((a, b) => {{
                const groupA = groups[a];
                const groupB = groups[b];
                // Sort by filter value first, then by color value
                if (groupA.filterValue !== groupB.filterValue) {{
                    return groupA.filterValue.localeCompare(groupB.filterValue);
                }}
                return groupA.colorValue.localeCompare(groupB.colorValue);
            }});

            sortedGroupKeys.forEach(key => {{
                const group = groups[key];
                const groupData = group.data;
                
                // Sort data by x-axis for proper line connections
                groupData.sort((a, b) => {{
                    const aVal = a[xColumn];
                    const bVal = b[xColumn];
                    
                    // Handle date strings
                    if (typeof aVal === 'string' && aVal.match(/\d{{4}}-\d{{2}}-\d{{2}}/)) {{
                        return new Date(aVal) - new Date(bVal);
                    }}
                    
                    // Handle numeric values
                    return aVal - bVal;
                }});
                
                // Calculate subplot position
                const filterRowIndex = selectedFilters.indexOf(group.filterValue);
                const yColIndex = currentYColumns.indexOf(group.yColumn);
                
                let xaxis = 'x';
                let yaxis = 'y';
                
                if (numFilterRows > 1 || numYCols > 1) {{
                    // Calculate subplot number (1-indexed)
                    const subplotNum = filterRowIndex * numYCols + yColIndex + 1;
                    
                    if (subplotNum > 1) {{
                        xaxis = `x${{subplotNum}}`;
                        yaxis = `y${{subplotNum}}`;
                    }}
                }}
                
                // Create unique legend group per filter-color combination
                const legendGroup = `${{group.filterValue}}_${{group.colorValue}}`;
                
                // Only show legend for first y column of each filter-color combination
                const showLegend = yColIndex === 0;
                
                // Parse x values as dates if they look like dates
                const xValues = groupData.map(row => {{
                    const xVal = row[xColumn];
                    // Try to parse as date if it's a string that looks like a date
                    if (typeof xVal === 'string' && xVal.match(/\d{{4}}-\d{{2}}-\d{{2}}/)) {{
                        return parseDate(xVal);
                    }}
                    return xVal;
                }});
                
                const trace = {{
                    x: xValues,
                    y: groupData.map(row => row[group.yColumn]),
                    mode: 'lines+markers',
                    type: 'scatter',
                    name: `${{group.filterValue}} - ${{group.colorValue}}`,
                    legendgroup: legendGroup,
                    showlegend: showLegend,
                    xaxis: xaxis,
                    yaxis: yaxis,
                    line: {{
                        color: colorMap[group.colorValue],
                        width: 2
                    }},
                    marker: {{
                        color: colorMap[group.colorValue],
                        size: 6,
                        line: {{
                            width: 1,
                            color: 'rgba(255,255,255,0.8)'
                        }}
                    }},
                    hovertemplate: `<b>${{group.colorValue}}</b><br>` +
                                `${{xColumn}}: %{{x}}<br>` +
                                `${{group.yColumn}}: %{{y}}<br>` +
                                `${{filterColumn}}: %{{customdata[0]}}<br>` +
                                '<extra></extra>',
                    customdata: groupData.map(row => [row[filterColumn]])
                }};
                traces.push(trace);
            }});
            
            return traces;
        }}

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
        
        // Create new traces using current dataset
        const traces = createPlotTraces(currentData, selectedFilters);
        
        // Create dynamic title
        const plotTitle = singleDataset ? baseTitle : `${{baseTitle}} - ${{currentDatasetName}}`;
        
        // Calculate subplot layout
        const numYCols = currentYColumns.length;
        
        // Create layout with subplots
        let layout = {{
            title: plotTitle,
            hovermode: 'closest',
            showlegend: true,
            height: Math.max(400, 300 * numFilterRows)
        }};
        
        if (numFilterRows > 1 || numYCols > 1) {{
            // Create subplot specifications
            const subplotSpecs = [];
            for (let row = 0; row < numFilterRows; row++) {{
                const rowSpecs = [];
                for (let col = 0; col < numYCols; col++) {{
                    rowSpecs.push({{}});
                }}
                subplotSpecs.push(rowSpecs);
            }}
            
            layout.grid = {{
                rows: numFilterRows,
                columns: numYCols,
                pattern: 'independent',
                roworder: 'top to bottom'
            }};
            
            // Add axis labels and titles for each subplot
            let subplotCounter = 1;
            for (let filterIdx = 0; filterIdx < selectedFilters.length; filterIdx++) {{
                const filterValue = selectedFilters[filterIdx];
                
                for (let yColIdx = 0; yColIdx < currentYColumns.length; yColIdx++) {{
                    const yColumn = currentYColumns[yColIdx];
                    
                    let xaxisKey = subplotCounter === 1 ? 'xaxis' : `xaxis${{subplotCounter}}`;
                    let yaxisKey = subplotCounter === 1 ? 'yaxis' : `yaxis${{subplotCounter}}`;
                    
                    // FIXED: Corrected anchor references
                    layout[xaxisKey] = {{
                        title: filterIdx === selectedFilters.length - 1 ? xColumn : '',
                        anchor: subplotCounter === 1 ? 'y' : `y${{subplotCounter}}`,
                        type: 'date'  // Set axis type to date for proper formatting
                    }};
                    layout[yaxisKey] = {{
                        title: yColIdx === 0 ? filterValue : '',
                        anchor: subplotCounter === 1 ? 'x' : `x${{subplotCounter}}`
                    }};
                    
                    // Add subplot titles
                    if (!layout.annotations) layout.annotations = [];
                    
                    // Y column title (top of column)
                    if (filterIdx === 0) {{
                        layout.annotations.push({{
                            text: `Y: ${{yColumn}}`,
                            showarrow: false,
                            x: (yColIdx + 0.5) / numYCols,
                            y: 1.02,
                            xref: 'paper',
                            yref: 'paper',
                            xanchor: 'center',
                            yanchor: 'bottom',
                            font: {{ size: 12, color: '#333' }},
                            textangle: 0
                        }});
                    }}
                    
                    subplotCounter++;
                }}
            }}
        }} else {{
            layout.xaxis = {{ 
                title: xColumn,
                type: 'date'  // Set axis type to date for proper formatting
            }};
            layout.yaxis = {{ title: currentYColumns[0] }};
        }}
        
        // Update plot
        Plotly.newPlot('plotDiv', traces, layout);
    }}
        
    

// BONUS: Add table sorting functionality
let sortColumn = null;
let sortDirection = 'asc';

function sortTable(column) {{
    const tableBody = document.getElementById('tableBody');
    const rows = Array.from(tableBody.querySelectorAll('tr'));
    
    // Toggle sort direction if clicking the same column
    if (sortColumn === column) {{
        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    }} else {{
        sortDirection = 'asc';
        sortColumn = column;
    }}
    
    // Get column index
    const headerCells = document.querySelectorAll('#tableHead th');
    let columnIndex = -1;
    headerCells.forEach((th, index) => {{
        if (th.textContent === column) {{
            columnIndex = index;
        }}
    }});
    
    if (columnIndex === -1) return;
    
    // Sort rows
    rows.sort((a, b) => {{
        const aVal = a.cells[columnIndex].textContent.trim();
        const bVal = b.cells[columnIndex].textContent.trim();
        
        // Try to parse as numbers
        const aNum = parseFloat(aVal.replace(/,/g, ''));
        const bNum = parseFloat(bVal.replace(/,/g, ''));
        
        let comparison = 0;
        if (!isNaN(aNum) && !isNaN(bNum)) {{
            comparison = aNum - bNum;
        }} else {{
            comparison = aVal.localeCompare(bVal);
        }}
        
        return sortDirection === 'asc' ? comparison : -comparison;
    }});
    
    // Clear and re-append sorted rows
    tableBody.innerHTML = '';
    rows.forEach(row => tableBody.appendChild(row));
    
    // Update header to show sort direction
    headerCells.forEach(th => {{
        th.classList.remove('sort-asc', 'sort-desc');
        if (th.textContent === column) {{
            th.classList.add(`sort-${{sortDirection}}`);
        }}
    }});
}}
        // Select all checkboxes
        function selectAll() {{
            const currentFilterValues = [...new Set(currentData.map(row => row[filterColumn]))].sort();
            currentFilterValues.forEach(value => {{
                const checkbox = document.getElementById(`filter_${{value}}`);
                if (checkbox) checkbox.checked = true;
            }});
            if (currentView === 'plot') {{
                updatePlot();
            }} else {{
                updateTable();
            }}
        }}
        
        // Deselect all checkboxes
        function deselectAll() {{
            const currentFilterValues = [...new Set(currentData.map(row => row[filterColumn]))].sort();
            currentFilterValues.forEach(value => {{
                const checkbox = document.getElementById(`filter_${{value}}`);
                if (checkbox) checkbox.checked = false;
            }});
            if (currentView === 'plot') {{
                updatePlot();
            }} else {{
                updateTable();
            }}
        }}
        
        // Initialize the application
        function initialize() {{
            initializeTabs();
            updateFilterCheckboxes();
            updateGroupByOptions();
            updatePlot();
        }}
        
        // Initialize when page loads
        initialize();
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
    
    # Dataset 1: Stock prices with multiple y variables
    dates1 = pd.date_range('2023-01-01', periods=100)
    stock_data = {
        'date': dates1,
        'price': np.random.normal(100, 15, 100) + np.random.normal(0, 3, 100).cumsum(),
        'volume': np.random.normal(1000, 200, 100),
        'volatility': np.random.normal(0.2, 0.05, 100),
        'quality': np.random.choice(['High', 'Medium', 'Low'], 100),
        'location': np.random.choice(['New York', 'London', 'Tokyo'], 100)
    }
    
    # Dataset 2: Crypto prices with different y variables
    dates2 = pd.date_range('2023-01-01', periods=120)
    crypto_data = {
        'date': dates2,
        'price': np.random.normal(50, 20, 120) + np.random.normal(0, 8, 120).cumsum(),
        'market_cap': np.random.normal(5000, 1000, 120),
        'transactions': np.random.normal(500, 100, 120),
        'quality': np.random.choice(['High', 'Medium', 'Low'], 120),
        'location': np.random.choice(['New York', 'London', 'Tokyo', 'Seoul'], 120)
    }
    
    # Create DataFrames
    datasets = {
        'Stocks': pd.DataFrame(stock_data),
        'Crypto': pd.DataFrame(crypto_data)
    }
    
    # Custom filter descriptions (these will be merged with defaults)
    custom_descriptions = {
        'Tokyo': 'Major Asian Financial Market - Custom Description'
    }
    
    # Example 1: Different y variables per dataset using dictionary
    y_config = {
        'Stocks': ['price', 'volume', 'volatility'],
        'Crypto': ['price', 'market_cap']
    }
    
    superPlotter(datasets, 
                x="date", 
                y=y_config, 
                color="quality", 
                filter="location",
                title="Multi-Y Market Analysis Dashboard",
                output_file="multi_y_demo.html",
                filter_descriptions=custom_descriptions)
    
    print("Enhanced multi-Y demo complete! Open 'multi_y_demo.html' in your browser.")
    print("Features:")
    print("- Filter labels now positioned on the right side of plots")
    print("- Filter checkboxes include descriptions for known locations")
    print("- Custom descriptions can be provided and will merge with defaults")
    
    # Example 2: Same y variables for all datasets using list
    superPlotter(datasets, 
                x="date", 
                y=['price'], 
                color="quality", 
                filter="location",
                title="Single Y Market Analysis",
                output_file="single_y_demo.html")
    
    print("Single-Y demo complete! Open 'single_y_demo.html' in your browser.")
    
    # Example 3: Single dataset with multiple y variables
    superPlotter(datasets['Stocks'], 
                x="date", 
                y=['price', 'volume', 'volatility'], 
                color="quality", 
                filter="location",
                title="Stock Analysis - Multiple Metrics",
                output_file="stock_multi_y_demo.html")
    
    print("Stock multi-Y demo complete! Open 'stock_multi_y_demo.html' in your browser.")
