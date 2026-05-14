let chartRegistry = {};
function drawSingleChart(canvasId, labels, values){
  const el = document.getElementById(canvasId);
  if(!el || typeof Chart === 'undefined') return;
  if(chartRegistry[canvasId]){ chartRegistry[canvasId].destroy(); chartRegistry[canvasId]=null; }
  chartRegistry[canvasId] = new Chart(el.getContext('2d'), {type:'bar',data:{labels:labels,datasets:[{label:'数量',data:values}]},options:{responsive:true,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true}}}});
}
window.addEventListener('beforeunload', ()=>{Object.values(chartRegistry).forEach(c=>{if(c)c.destroy();}); chartRegistry={};});
