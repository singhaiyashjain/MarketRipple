/** Cytoscape stylesheet = the visual language. Update Legend.jsx when changing. */
export const graphStyle = [
  { selector: 'node', style: {
      label: 'data(label)', 'font-family': 'Hanken Grotesk, system-ui, sans-serif', 'font-size': 11, 'font-weight': 500,
      color: '#14213d', 'text-valign': 'bottom', 'text-margin-y': 6, 'text-wrap': 'wrap', 'text-max-width': 96,
      'text-background-color': '#f7f9fb', 'text-background-opacity': 0.9, 'text-background-padding': 3, 'text-background-shape': 'roundrectangle',
      'background-color': 'data(color)', shape: 'data(shape)', width: 'data(size)', height: 'data(size)',
      'border-width': 3, 'border-color': '#ffffff', 'shadow-blur': 12, 'shadow-color': '#14213d', 'shadow-opacity': 0.25, 'shadow-offset-x': 0, 'shadow-offset-y': 3,
  } },
  { selector: 'edge', style: {
      width: 'data(width)', 'line-color': '#9aa6b8', 'target-arrow-color': '#9aa6b8', 'target-arrow-shape': 'triangle',
      'arrow-scale': 0.9, 'curve-style': 'bezier', 'line-cap': 'round', opacity: 0.9, label: 'data(sign)', 'font-size': 12, 'font-weight': 700, color: '#5b6b82',
      'text-background-color': '#f7f9fb', 'text-background-opacity': 1, 'text-background-padding': 2, 'text-background-shape': 'roundrectangle',
  } },
  { selector: 'edge[inferred = 1]', style: {
      'line-style': 'dashed', 'line-dash-pattern': [6, 4], 'line-color': '#b7791f', 'target-arrow-color': '#b7791f', color: '#b7791f',
  } },
  { selector: 'edge[quant = 1]', style: { 'line-color': '#0e7c66', 'target-arrow-color': '#0e7c66', color: '#0e7c66' } },
  { selector: '.dim', style: { opacity: 0.14 } },
  { selector: 'edge.hl', style: { 'line-color': '#3b4bdb', 'target-arrow-color': '#3b4bdb', color: '#3b4bdb', 'z-index': 10 } },
  { selector: 'node.hl', style: { 'border-color': '#3b4bdb', 'border-width': 3 } },
  { selector: '.sel', style: { 'overlay-color': '#3b4bdb', 'overlay-opacity': 0.14, 'overlay-padding': 7 } },
  { selector: '.hide', style: { display: 'none' } },
  { selector: '.future', style: { display: 'none' } },
]
