import base64
import io

from dash import Dash, dcc, html, dash_table, Input, Output, State, MATCH, no_update
import plotly.express as px
import pandas as pd

app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server

app.layout = html.Div([
    html.H1('Upload TindaPay Dashboard Data', style={'textAlign': 'center'}),
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            'Drag and Drop or ',
            html.A('Select Files')
        ]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        multiple=True
    ),
    html.Div(id='output-data-upload', children=[]),
    html.Div(id='outlet-data-container', children=[
        html.H2('Outlet Data', style={'textAlign': 'center'}),
        dash_table.DataTable(
            id='outlet-table',
            columns=[
                {'name': 'Outlet Code', 'id': 'Outlet Code'},
                {'name': 'Outlet Name', 'id': 'Outlet Name'},
                {'name': 'Amount Pending', 'id': 'Amount Pending'},
                {'name': 'Ageing', 'id': 'Ageing'}
            ],
            style_data_conditional=[
                {
                    'if': {'filter_query': '{Ageing} < 7', 'column_id': 'Ageing'},
                    'backgroundColor': 'green',
                    'color': 'white'
                },
                {
                    'if': {'filter_query': '{Ageing} = 7', 'column_id': 'Ageing'},
                    'backgroundColor': 'yellow',
                    'color': 'black'
                },
                {
                    'if': {'filter_query': '{Ageing} >= 8', 'column_id': 'Ageing'},
                    'backgroundColor': 'red',
                    'color': 'white'
                },
            ],
        ),
    ], style={'display': 'none'}),
])

@app.callback(
    [Output('output-data-upload', 'children'),
     Output('outlet-table', 'data'),
     Output('outlet-data-container', 'style')],
    [Input('upload-data', 'contents')],
    [State('upload-data', 'filename'),
     State('upload-data', 'last_modified'),
     State('output-data-upload', 'children')],
    prevent_initial_call=True
)
def update_output(contents, filename, date, children):
    outlet_data = []
    if contents is not None:
        for i, (c, n, d) in enumerate(zip(contents, filename, date)):
            content_type, content_string = c.split(',')
            decoded = base64.b64decode(content_string)
            try:
                if 'csv' in n:
                    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
                elif 'xls' in n:
                    # Reading multiple sheets
                    df_usage = pd.read_excel(io.BytesIO(decoded), sheet_name="1. USAGE", skiprows=3, usecols='B:C')
                    df_repeat = pd.read_excel(io.BytesIO(decoded), sheet_name="2. REPEAT", skiprows=3, usecols='B:D')
                    df_repayment = pd.read_excel(io.BytesIO(decoded), sheet_name="3. REPAYMENT", skiprows=3, usecols='B:E', nrows=14)
                    df_repayment2 = pd.read_excel(io.BytesIO(decoded), sheet_name="3. REPAYMENT", skiprows=20, usecols='B:E', nrows=14)
                    df_outlet = pd.read_excel(io.BytesIO(decoded), sheet_name="3. REPAYMENT", skiprows=40, usecols='B:E', nrows=11)
                    df_gsv1 = pd.read_excel(io.BytesIO(decoded), sheet_name="4. IMPACT TO GSV", skiprows=3, usecols='B:D', nrows=4)

                    df_buy1 = pd.read_excel(io.BytesIO(decoded), sheet_name="4. IMPACT TO GSV", skiprows=11, usecols='B:D', nrows=4)

                    df_buy2 = pd.read_excel(io.BytesIO(decoded), sheet_name="4. IMPACT TO GSV", skiprows=19, usecols='B:D', nrows=4)

                    df_dict = {'1. USAGE': df_usage, '2. REPEAT': df_repeat, '3. REPAYMENT 1': df_repayment, '3. REPAYMENT 2': df_repayment2, '4. IMPACT TO GSV': df_gsv1, '4. IMPACT TO GSV 2': df_buy1, '4. IMPACT TO GSV 3': df_buy2}

                    outlet_data = df_outlet.to_dict('records')

                for sheet_name, df in df_dict.items():
                    children.append(html.Div([
                        html.H5(f'{n} - {sheet_name}'),
                        dash_table.DataTable(
                            data=df.to_dict('records'),
                            columns=[{'name': col, 'id': col, 'selectable': True} for col in df.columns],
                            page_size=5,
                            filter_action='native',
                            column_selectable='single',
                            selected_columns=[df.columns[1]] if len(df.columns) >= 1 else [],
                            style_table={'overflowX': 'auto'},
                            id={'type': 'dynamic-table', 'index': f'{i}-{sheet_name}'},
                        ),
                        dcc.Graph(
                            id={'type': 'dynamic-graph', 'index': f'{i}-{sheet_name}'},
                            figure={}
                        ),
                        html.Hr()
                    ]))
            except Exception as e:
                print(e)
                return html.Div(['There was an error processing this file.'])
        return children, outlet_data, {'display': 'block'}
    return "", outlet_data, {'display': 'none'}

@app.callback(
    Output({'type': 'dynamic-graph', 'index': MATCH}, 'figure'),
    Input({'type': 'dynamic-table', 'index': MATCH}, 'derived_virtual_indices'),
    Input({'type': 'dynamic-table', 'index': MATCH}, 'selected_columns'),
    State({'type': 'dynamic-table', 'index': MATCH}, 'data'))
def create_graphs(filtered_data, selected_col, all_data):
    if filtered_data is not None:
        dff = pd.DataFrame(all_data)
        dff = dff.loc[filtered_data]
        print(dff.columns)

        if 'WK' in dff.columns:
            print("hii")
            print(selected_col, "selected col")
            if selected_col and selected_col[0] != 'Year':
                print("hi0")
                dff = dff.groupby('WK')[selected_col[0]].mean().reset_index()
                return px.line(dff, x='WK', y=selected_col[0])
        elif 'WK_r' in dff.columns:
            fig = px.bar(dff, x='WK_r', y=['REPEAT', 'NEW'], title="Weekly Repeat and New Counts", 
                        labels={'value': 'Count', 'variable': 'Type'}, barmode='stack')
            return fig
        elif 'WK_1' in dff.columns:
             if 'Paid' in dff.columns and 'Outstanding' in dff.columns:
                # Replace '-' with 0 in 'Outstanding'
                dff['Outstanding'] = dff['Outstanding'].replace('-', 0).astype(float)
                fig = px.bar(
                    dff,
                    x='WK_1',
                    y=['Paid', 'Outstanding'],
                    title='Total, Paid, and Outstanding Balances',
                    labels={'value': 'Amount', 'variable': 'Balance Type'},
                    barmode='stack'
                )
                fig.update_layout(xaxis_title='Week', yaxis_title='Amount')
                return fig
        elif 'WK_2' in dff.columns:
             if 'Paid' in dff.columns and 'Outstanding' in dff.columns:
                # Replace '-' with 0 in 'Outstanding'
                dff['Outstanding'] = dff['Outstanding'].replace('-', 0).astype(float)
                fig = px.bar(
                    dff,
                    x='WK_2',
                    y=['Paid', 'Outstanding'],
                    title='Total, Paid, and Outstanding Balances',
                    labels={'value': 'Amount', 'variable': 'Balance Type'},
                    barmode='stack'
                )
                fig.update_layout(xaxis_title='Week', yaxis_title='Amount')
                return fig
        elif 'REPEAT' in dff.columns and 'NEW' in dff.columns:
            fig = px.bar(dff, x='WK', y=['REPEAT', 'NEW'], title="Weekly Repeat and New Counts",
                         labels={'value': 'Count', 'variable': 'Type'}, barmode='stack')
            return fig
        elif 'Month_GSV' in dff.columns and 'GSV (PHP)' in dff.columns:
            fig = px.bar(dff, x='Month_GSV', y=['GSV (PHP)', 'Growth vs Baseline'], title="GSV",
                         labels={'value': 'Count', 'variable': 'Type'}, barmode='stack')
            return fig
        elif 'Month_BF' in dff.columns and 'No. of Invoices' in dff.columns:
            fig = px.bar(dff, x='Month_BF', y=['No. of Invoices', 'Growth vs Baseline'], title="GSV",
                         labels={'value': 'Count', 'variable': 'Type'}, barmode='stack')
            return fig
        elif 'Month' in dff.columns and 'Grew vs. Baseline' in dff.columns:
            fig = px.bar(dff, x='Month', y=['Grew vs. Baseline', 'Did not grow vs. Baseline'], title="GSV",
                         labels={'value': 'Count', 'variable': 'Type'}, barmode='stack')
            return fig
    return {}

if __name__ == '__main__':
    app.run_server(debug=True)
