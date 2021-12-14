from dash import html, dcc, Dash
from dash.dependencies import Input, Output

import dash_bootstrap_components as dbc
import plotly.express as px
import nfl_data_py as nfl


# the columns from the nfl pbp data we will use and their dtypes
cols_i_want = {
    'season':'category',
    'week':'category',
    'player_name':'category',
    'recent_team':'category',
    'targets':'int',
    'receptions':'int',
    'target_share':'float'
}

# pull the columns for the 2021 season
# since we're going to do our own dtype conversion, dont bother downcasting floats
df = nfl.import_weekly_data([2021], columns=list(cols_i_want), downcast=False)

# dtype conversions to reduce memory footprint
df['season'] = df.season.astype('category')
for k, v in cols_i_want.items():
    df[k] = df[k].astype(v)

df['week'] = df.week.cat.as_ordered()

# subset to >0 targets
df = df.loc[df.targets > 0]

df.rename({"recent_team":"team"}, axis=1, inplace=True)

player_rks = df.groupby(['team','player_name'], observed=True)
player_rks = player_rks['targets'].sum().reset_index()
player_rks['nfl_rank'] = player_rks.targets.rank(method='min',ascending=False).astype('int16')
player_rks['team_rank'] = player_rks.groupby('team')['targets'].rank(method='min',ascending=False).astype('int16')
player_rks.rename({"targets":"season_targets"}, axis=1, inplace=True)

slider_marks = {i:str(i) for i  in range(2,11,2)}
# slider_marks.update({i:"" for i in range(3,10,2)})

app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
app.title = "NFL Targets"

server = app.server

app.layout = html.Div([
    html.H2("NFL Target Share Viz App"),
    html.Div(
        id = 'controls',
        className = "two columns",
        children = [
            html.H6('Select a team:'),
            dcc.Dropdown(
                    options=[dict(label=tm, value=tm) for tm in (sorted(df.team.unique()))],
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
        (player_rks['team'] == selected_team)
        &
        (player_rks['team_rank'] <= num_receivers)
    ]

    players = players.merge(df)

    fig = px.area(players, x='week', 
        y='target_share' if normalize else 'targets', 
        color='player_name', hover_data=['targets'],
        # groupnorm="percent" if normalize else None,
        labels={
            "player_name":"Player",
            "week":"Week",
            "targets":"Targets",
            "target_share":"Target Share"
        },
        category_orders={
            'week':[str(i) for i in range(1,players.week.max()+1)]
        },
        template='plotly_dark'
    )
    fig.update_xaxes(type="category")
    if normalize:
        fig.update_yaxes(tickformat=',.0%')

    fig.update_layout(
        {"plot_bgcolor": "rgba(0, 0, 0, 0)", "paper_bgcolor": "rgba(0, 0, 0, 0)"}
    )

    return fig


if __name__ == '__main__':
    app.run_server(debug=True)