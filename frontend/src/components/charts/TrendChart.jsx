import ReactEChartsCore from 'echarts-for-react/lib/core'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

// Register only the pieces ECharts needs for a line chart. This keeps the
// production bundle far smaller than importing the whole library.
echarts.use([
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  DataZoomComponent,
  CanvasRenderer,
])

/** Reusable time-series chart powered by Apache ECharts. */
export default function TrendChart({
  title, series = [], height = 280, unit, xField = 'time', axisType = 'time',
}) {
  const option = {
    title: title ? { text: title, textStyle: { fontSize: 13, fontWeight: 600 } } : undefined,
    tooltip: { trigger: 'axis' },
    legend: { top: title ? 28 : 0, type: 'scroll' },
    grid: { left: 55, right: 20, top: title ? 65 : 40, bottom: 35 },
    xAxis: {
      type: axisType,
      axisLabel: {
        fontSize: 10,
        ...(axisType === 'value' ? { formatter: (value) => `${value}h` } : {}),
      },
      ...(axisType === 'value' ? { name: 'Elapsed time' } : {}),
    },
    yAxis: {
      type: 'value',
      name: unit || '',
      scale: true,
      axisLabel: { fontSize: 10 },
    },
    dataZoom: [{ type: 'inside' }],
    series: series.map((item) => ({
      name: item.name || item.code,
      type: 'line',
      showSymbol: false,
      smooth: true,
      connectNulls: false,
      data: (item.points || []).map((point) => [point[xField], point.value]),
    })),
  }

  if (series.every((item) => !item.points?.length)) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-slate-400">
        No data for the selected filters
      </div>
    )
  }

  return <ReactEChartsCore echarts={echarts} option={option} style={{ height }} notMerge />
}
