# SPDX-FileCopyrightText: 2024-present Oori Data <info@oori.dev>
#
# SPDX-License-Identifier: Apache-2.0
# arkestra.metrics.textdiff_dataviz
'''
Tools for metrics (AKA evaluations) for data & GenAI pipelines ops

3 visualization methods implemented, each with its own advantages:
- Heatmap provides a clear overview of all similarities at once
- HTML table is interactive and can be shared easily
- Plotly 3D visualization allows for interactive exploration of the relationships
'''
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from utiloori.plaintext import truncate_text_middle


def similarities_heatmap(reftexts, target_texts, similarities, model_name):
    '''
    Build a similarity heatmap using Seaborn/Matplotlib from texts being compared via some 0.0-1.0 normalized method
    (e.g. vector cosine similarity)
    '''
    # Create a DataFrame for the heatmap
    df = pd.DataFrame(similarities, 
                     index=[f'Ref {i+1}: {text[:30]}...' for i, text in enumerate(reftexts)],
                     columns=[f'Target {i+1}: {text[:30]}...' for i, text in enumerate(target_texts)])
    
    # Create heatmap
    plt.figure(figsize=(12, 8))
    sns.heatmap(df, annot=True, cmap='RdYlBu', center=0.5)
    plt.title(f'Similarity Scores - {model_name}')
    plt.tight_layout()
    plt.show()


def html_table_viz(reftexts, target_texts, similarities_dict):
    '''
    Build interactive HTML table viz from texts being compared via some 0.0-1.0 normalized method
    (e.g. vector cosine similarity)

    Clean, color-coded HTML viz.
    Similarity scores shown with a color gradient from red (low similarity) to blue (high similarity).
    '''
    html = '''
    <html>
    <head>
        <style>
            table { border-collapse: collapse; margin: 20px 0; }
            th, td { padding: 8px; border: 1px solid #ddd; }
            .similarity-cell { 
                width: 80px; 
                text-align: center; 
                color: white;
                text-shadow: 1px 1px 1px rgba(0,0,0,0.5);
            }
        </style>
    </head>
    <body>
    '''
    
    for model_name, similarities in similarities_dict.items():
        html += f'<h2>{model_name}</h2>'
        html += '<table>'
        
        # Header row
        html += '<tr><th></th>'
        for j, target in enumerate(target_texts):
            html += f'<th>Target {j+1}: {target[:50]}...</th>'
        html += '</tr>'

        for j, target in enumerate(target_texts):
            truncated = truncate_text_middle(target)
            html += f"<th>Target {j+1}: {truncated}</th>"
        html += "</tr>"

        # Data rows
        for i, ref in enumerate(reftexts):
            html += f'<tr><th>Ref {i+1}: {ref[:50]}...</th>'
            for j, _ in enumerate(target_texts):
                similarity = similarities[i][j]
                # Calculate background color (blue for high similarity, red for low)
                r = int(255 * (1 - similarity))
                b = int(255 * similarity)
                html += f"<td class='similarity-cell' style='background-color: rgb({r},0,{b})'>{similarity:.4f}</td>"
            html += '</tr>'
        
        html += '</table><br><br>'
    
    html += '</body></html>'
    
    with open('similarities_visualization.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print('Visualization saved to similarities_visualization.html')


def plotly_3d_viz(reftexts, target_texts, similarities, model_name):
    '''
    Build a, interactive Plotly visualization from texts being compared via some 0.0-1.0 normalized method
    (e.g. vector cosine similarity)
    '''
    x = []
    y = []
    z = []
    text = []
    
    # Convert similarities to regular numpy array/Python floats
    similarities = np.array(similarities).astype(float)
    
    for i, ref in enumerate(reftexts):
        for j, target in enumerate(target_texts):
            x.append(i)
            y.append(j)
            z.append(float(similarities[i][j]))  # Ensure we're using regular Python float
            text.append(f'Ref: {ref[:30]}...<br>Target: {target[:30]}...<br>Score: {similarities[i][j]:.4f}')
    
    fig = go.Figure(data=[go.Scatter3d(
        x=x, y=y, z=z,
        mode='markers',
        marker=dict(
            size=8,
            color=z,
            colorscale='RdYlBu',
            showscale=True
        ),
        text=text,
        hoverinfo='text'
    )])
    
    fig.update_layout(
        title=f'Similarity Scores - {model_name}',
        scene=dict(
            xaxis_title='Reference Text Index',
            yaxis_title='Target Text Index',
            zaxis_title='Similarity Score'
        )
    )
    fig.show()


'''
Ways to share these visualizations

1. **Via FastAPI Endpoint** - Serve the Plotly visualization as an HTML page:

```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import plotly

app = FastAPI()

@app.get('/plot/{model_name}', response_class=HTMLResponse)
async def get_plot(model_name: str):
    # Generate your plot here using create_3d_visualization
    fig = create_3d_visualization(reftexts, target_texts, similarities, model_name)
    
    # Convert to HTML
    plot_html = plotly.io.to_html(fig, full_html=True, include_plotlyjs=True)
    return HTMLResponse(content=plot_html)
```

2. **Save as HTML file** that can be shared on Google Drive or uploaded to Notion:

```python
def create_3d_visualization(reftexts, target_texts, similarities, model_name):
    # ... existing plot creation code ...
    
    # Save to HTML file
    fig.write_html(f'similarity_plot_{model_name}.html')
    
    # Optionally still show in browser
    fig.show()
```

3. **Create a Plotly Chart Studio** version (can be embedded anywhere):

```python
import chart_studio.plotly as py
import chart_studio

def create_3d_visualization(reftexts, target_texts, similarities, model_name):
    # First, set up your credentials
    chart_studio.tools.set_credentials_file(
        username='your_plotly_username', 
        api_key='your_api_key'
    )
    
    # ... existing plot creation code ...
    
    # Upload to Chart Studio
    url = py.plot(fig, filename=f'similarity_plot_{model_name}', auto_open=False)
    print(f'Plot available at: {url}')
    
    return fig
```

4. **Save as static image** (less interactive but very portable):

```python
def create_3d_visualization(reftexts, target_texts, similarities, model_name):
    # ... existing plot creation code ...
    
    # Save as static image
    fig.write_image(f'similarity_plot_{model_name}.png')  # Requires kaleido package
    fig.write_image(f'similarity_plot_{model_name}.pdf')
    
    return fig
```

5. **Create an interactive dashboard** using Dash (for more complete web app):

```python
from dash import Dash, html, dcc
import dash_bootstrap_components as dbc

app = Dash(__name__)

app.layout = html.Div([
    html.H1('Embedding Similarity Visualization'),
    dcc.Dropdown(
        id='model-selector',
        options=[{'label': k, 'value': k} for k in MODELS.keys()],
        value=list(MODELS.keys())[0]
    ),
    dcc.Graph(id='similarity-plot')
])

@app.callback(
    Output('similarity-plot', 'figure'),
    Input('model-selector', 'value')
)
def update_graph(model_name):
    # Generate plot for selected model
    return create_3d_visualization(reftexts, target_texts, similarities_dict[model_name], model_name)

if __name__ == '__main__':
    app.run_server(debug=True)
```

For FastAPI server, either:
1. Serving the static HTML version via endpoint
2. Setting up a dedicated /plots route that serves the visualizations

Here's a more complete FastAPI implementation:

```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()

# Serve static files
app.mount('/static', StaticFiles(directory='static'), name='static')

@app.get('/plots/{model_name}/html', response_class=HTMLResponse)
async def get_plot_html(model_name: str):
    if model_name not in MODELS:
        raise HTTPException(status_code=404, detail='Model not found')
        
    fig = create_3d_visualization(reftexts, target_texts, similarities_dict[model_name], model_name)
    plot_html = plotly.io.to_html(fig, full_html=True, include_plotlyjs=True)
    return HTMLResponse(content=plot_html)

@app.get('/plots/{model_name}/png')
async def get_plot_png(model_name: str):
    if model_name not in MODELS:
        raise HTTPException(status_code=404, detail='Model not found')
    
    filename = f'static/plots/similarity_plot_{model_name}.png'
    
    # Create plot if it doesn't exist
    if not os.path.exists(filename):
        fig = create_3d_visualization(reftexts, target_texts, similarities_dict[model_name], model_name)
        fig.write_image(filename)
    
    return FileResponse(filename)
```

For sharing in Notion:
1. The HTML file can be added as a file attachment
2. The PNG version can be embedded directly in the page
3. If Chart Studio, can embed the interactive plot using the iframe embed code they provide
'''