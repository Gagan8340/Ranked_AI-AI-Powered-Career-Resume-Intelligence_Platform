const rawData = [{"date": "2026-06-20T15:27:41", "score": 36}];
let processedData = rawData;
if (processedData.length > 100) {
  // Aggregate
} else if (processedData.length === 1) {
  processedData = [
    { score: 0, date: processedData[0].date },
    processedData[0]
  ];
}

const labels = processedData.length === 2 && processedData[0].score === 0 ? ['Start', 'Current'] : processedData.map((_, i) => `Scan ${i + 1}`);
const dataPoints = processedData.map(d => d.score);

console.log("Labels:", labels);
console.log("Data:", dataPoints);
