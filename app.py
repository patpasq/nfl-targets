from dash import html, dcc, Dash
from dash.dependencies import Input, Output

import dash_bootstrap_components as dbc
import plotly.express as px
import nfl_data_py as nfl


# the columns from the nfl pbp data we will use and their dtypes
cols_i_want = {
    'week':'category',
    'posteam':'category',
    'pass_attempt':'bool',
    'complete_pass':'bool',
    'receiver_player_name':'category',
}

# pull the columns for the 2021 season
# since we're going to do our own dtype conversion, dont bother downcasting floats
df = nfl.import_pbp_data([2021], columns=list(cols_i_want), downcast=False)

# dtype conversions to reduce memory footprint
df['season'] = df.season.astype('category')
for k, v in cols_i_want.items():
    df[k] = df[k].astype(v)

# remove nan rows
df = df.loc[df.posteam.notna()]

# subset to only pass attempts
df = df.loc[df.pass_attempt].reset_index(drop=True)

# group by team, receiver, week
df = df.groupby(['week','posteam','receiver_player_name'], observed=True)
df = df['week'].count()
df.name = 'targets'
df = df.reset_index()

player_rks = df.groupby(['posteam','receiver_player_name'], observed=True)
player_rks = player_rks['targets'].sum().reset_index()
player_rks['nfl_rank'] = player_rks.targets.rank(method='min',ascending=False).astype('int16')
player_rks['team_rank'] = player_rks.groupby('posteam')['targets'].rank(method='min',ascending=False).astype('int16')
player_rks.rename({"targets":"season_targets"}, axis=1, inplace=True)

slider_marks = {i:str(i) for i  in range(2,11,2)}
# slider_marks.update({i:"" for i in range(3,10,2)})

app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])

server = app.server

app.layout = html.Div([
    html.H2("NFL Target Share Viz App"),
    html.Div(
        id = 'controls',
        className = "two columns",
        children = [
            html.H6('Select a team:'),
            dcc.Dropdown(
                    options=[dict(label=tm, value=tm) for tm in (sorted(df.posteam.unique()))],
                    value='CAR',
                    className='dbc_dark',
                    id='team-dropdown'
                ),
            html.Br(),
            html.H6('Max # of Receivers'),
            dcc.Slider(
                min=2,
                max=10,
                marks=slider_marks,
                value=5,
                className="dbc_pulse",
                id='num-receivers-slider'
            ),
            html.Br(),
            html.Div([
                html.H6(
                    'Normalize',
                    style={'width': '70%', 'display': 'inline-block'}),
                dbc.Switch(
                    id='normalize',
                    value=False,
                    style={'display': 'inline-block'}
                )
            ])
        ]
    ),
    html.Div(
        id='graph container',
        className = 'ten columns',
        children = [
            dcc.Graph(id='targets-graph')
        ]
    )
])


@app.callback(
    Output('targets-graph', 'figure'),
    Input('team-dropdown', 'value'),
    Input('num-receivers-slider', 'value'),
    Input('normalize', 'value'))
def update_figure(selected_team, num_receivers, normalize):
    players = player_rks.loc[
        (player_rks['posteam'] == selected_team)
        &
        (player_rks['team_rank'] <= num_receivers)
    ]

    players = players.merge(df)

    fig = px.area(players, x='week', y='targets', 
        color='receiver_player_name', hover_data=['targets'],
        groupnorm="percent" if normalize else None,
        labels={
            "receiver_player_name":"Player",
            "week":"Week",
            "targets":"Target Share" if normalize else "Targets"
        },
        template='plotly_dark'
    )
    fig.update_xaxes(type="category")
    if normalize:
        fig.update_yaxes(ticksuffix="%")
    fig.update_layout(
        {"plot_bgcolor": "rgba(0, 0, 0, 0)", "paper_bgcolor": "rgba(0, 0, 0, 0)"}
    )

    return fig


if __name__ == '__main__':
    app.run_server(debug=True)