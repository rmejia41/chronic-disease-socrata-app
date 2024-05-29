from sodapy import Socrata
import pandas as pd
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objs as go
import dash_mantine_components as dmc
from dotenv import load_dotenv
import os

import os

# Load environment variables from .env file
load_dotenv()

# Read CDC open data
data_url = os.getenv('DATA_URL')
data_set = os.getenv('DATA_SET')
app_token = os.getenv('APP_TOKEN')

client = Socrata(data_url, app_token)
client.timeout = 90
results = client.get(data_set, limit=1500000)
df = pd.DataFrame.from_records(results)

# Selecting specific columns
selected_columns = ['yearend', 'locationabbr', 'locationdesc', 'datasource', 'question', 'datavaluetype', 'datavalue', 'stratification1', 'stratificationcategoryid1']
dff = df[selected_columns]

# Transpose the dataset
dff_transposed = dff.pivot_table(
    index=['yearend', 'locationabbr', 'locationdesc', 'datasource', 'datavaluetype', 'stratification1', 'stratificationcategoryid1'],
    columns='question',
    values='datavalue',
    aggfunc='first'
).reset_index()

# Sort the transposed dataset
dff_transposed_sorted = dff_transposed.sort_values(by=['yearend', 'locationabbr', 'locationdesc'])

# Rename 'Stratification1' column to 'Demographic'
dff_transposed_sorted.rename(columns={'stratification1': 'Demographic'}, inplace=True)

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.MATERIA])
server = app.server

# Prepare dropdown options
year_options = [{'label': 'No Selection', 'value': 'No Selection'}] + \
               [{'label': year, 'value': year} for year in dff_transposed_sorted['yearend'].unique()]
health_indicator_options = [{'label': 'No Selection', 'value': 'No Selection'}] + \
                           [{'label': indicator, 'value': indicator} for indicator in dff_transposed_sorted.columns[7:]]

# App layout
app.layout = dbc.Container([
    html.H1("U.S. Chronic Disease Indicators (CDI) Dashboard", className="text-center mb-3"),
    dbc.Row([
        dbc.Col([
            html.Label("Select Year:"),
            dcc.Dropdown(
                id='year_dropdown',
                options=year_options,
                value='No Selection',
                style={'width': '100%'}  # Ensures dropdown stretches to column width
            ),
        ], width=6, md=3),  # Adjust column width for different screen sizes
        dbc.Col([
            html.Label("Select Health Indicator:"),
            dcc.Dropdown(
                id='health_indicator_dropdown',
                options=health_indicator_options,
                value='No Selection',
                style={'width': '100%', 'minWidth': '1200px'}  # Makes dropdown wider while ensuring it matches year dropdown alignment
            ),
        ], width=6, md=4),  # Increase md value to make the column wider on medium screens
    ]),
    dbc.Row([
        dbc.Col([
            dmc.Anchor(
                "CDC Source Link",
                href="https://data.cdc.gov/Chronic-Disease-Indicators/U-S-Chronic-Disease-Indicators-CDI-/g4ie-h725/about_dat",
                className="mt-1",
                style={"display": "block"}
            )
        ], width=12),
    ], justify="start"),
    dbc.Row([
        dbc.Col(dcc.Graph(id='us_map'), width=12)
    ], className="mt-1"),
    dbc.Row([
        dbc.Col(dcc.Graph(id='indicator_chart'), width=12)
    ], className="mt-3"),
], fluid=True)


@app.callback(
    [Output('us_map', 'figure'),
     Output('indicator_chart', 'figure')],
    [Input('year_dropdown', 'value'),
     Input('health_indicator_dropdown', 'value')]
)
def update_output(selected_year, selected_health_indicator):
    if selected_year == 'No Selection' or selected_health_indicator == 'No Selection':
        empty_map = go.Figure()
        return empty_map

    filtered_df = dff_transposed_sorted[dff_transposed_sorted['yearend'] == selected_year] if selected_year != 'No Selection' else dff_transposed_sorted
    if selected_health_indicator != 'No Selection':
        filtered_df[selected_health_indicator] = pd.to_numeric(filtered_df[selected_health_indicator], errors='coerce')
        filtered_df = filtered_df.dropna(subset=[selected_health_indicator])

    us_map = px.choropleth(
        filtered_df,
        locations='locationabbr',
        locationmode="USA-states",
        color=selected_health_indicator,
        color_continuous_scale=px.colors.sequential.Plasma,
        hover_name='locationdesc',
        hover_data={'datasource': True, 'datavaluetype': True, 'Demographic': True},
        scope="usa"
    )

    indicator_chart = px.bar(
        filtered_df,
        x='Demographic',
        y=selected_health_indicator,
        labels={'Demographic': 'Demographic'},
        title=f"{selected_health_indicator} by Demographic"
    )
    indicator_chart.update_layout(
        font=dict(size=10),
        width=800,
        height=400,
        margin=dict(l=50, r=50, t=50, b=50),
        yaxis=dict(title='', showticklabels=False)
    )

    return us_map, indicator_chart

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8050))
    app.run_server(debug=False, host='0.0.0.0', port=port)