# SPDX-FileCopyrightText: 2024-present Oori Data <info@oori.dev>
#
# SPDX-License-Identifier: Apache-2.0
# arkestra.metrics.textdiff_dataviz
'''
Tools for metrics (AKA evaluations) for data & GenAI pipelines ops
'''
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 3 visualization methods implemented, each with its own advantages:
# - Heatmap provides a clear overview of all similarities at once
# - HTML table is interactive and can be shared easily
# - Plotly 3D visualization allows for interactive exploration of the relationships


def similarities_heatmap(reftexts, target_texts, similarities, model_name):
    """
    Build a similarity heatmap using Seaborn/Matplotlib from texts being compared via some 0.0-1.0 normalized method
    (e.g. vector cosine similarity)
    """
    # Create a DataFrame for the heatmap
    df = pd.DataFrame(similarities, 
                     index=[f"Ref {i+1}: {text[:30]}..." for i, text in enumerate(reftexts)],
                     columns=[f"Target {i+1}: {text[:30]}..." for i, text in enumerate(target_texts)])
    
    # Create heatmap
    plt.figure(figsize=(12, 8))
    sns.heatmap(df, annot=True, cmap='RdYlBu', center=0.5)
    plt.title(f'Similarity Scores - {model_name}')
    plt.tight_layout()
    plt.show()


def html_table_viz(reftexts, target_texts, similarities_dict):
    """
    Build interactive HTML table viz from texts being compared via some 0.0-1.0 normalized method
    (e.g. vector cosine similarity)

    Clean, color-coded HTML viz.
    Similarity scores shown with a color gradient from red (low similarity) to blue (high similarity).
    """
    html = """
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
    """
    
    for model_name, similarities in similarities_dict.items():
        html += f"<h2>{model_name}</h2>"
        html += "<table>"
        
        # Header row
        html += "<tr><th></th>"
        for j, target in enumerate(target_texts):
            html += f"<th>Target {j+1}: {target[:50]}...</th>"
        html += "</tr>"
        
        # Data rows
        for i, ref in enumerate(reftexts):
            html += f"<tr><th>Ref {i+1}: {ref[:50]}...</th>"
            for j, _ in enumerate(target_texts):
                similarity = similarities[i][j]
                # Calculate background color (blue for high similarity, red for low)
                r = int(255 * (1 - similarity))
                b = int(255 * similarity)
                html += f'<td class="similarity-cell" style="background-color: rgb({r},0,{b})">{similarity:.4f}</td>'
            html += "</tr>"
        
        html += "</table><br><br>"
    
    html += "</body></html>"
    
    with open("similarities_visualization.html", "w", encoding='utf-8') as f:
        f.write(html)
    
    print("Visualization saved to similarities_visualization.html")


def plotly_3d_viz(reftexts, target_texts, similarities, model_name):
    """
    Build a, interactive Plotly visualization from texts being compared via some 0.0-1.0 normalized method
    (e.g. vector cosine similarity)
    """
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
            text.append(f"Ref: {ref[:30]}...<br>Target: {target[:30]}...<br>Score: {similarities[i][j]:.4f}")
    
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
