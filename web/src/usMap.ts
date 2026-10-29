// Contiguous-US projection and halftone dots. The map itself is drawn as dots.
import { geoAlbers, geoPath, type GeoProjection } from 'd3-geo'
import { merge } from 'topojson-client'
import type { GeometryCollection, Topology } from 'topojson-specification'
import states from 'us-atlas/states-10m.json'

export const MAP_W = 864
export const MAP_H = 464
const GRID = 11

// Leave out Alaska, Hawaii and overseas territories
const OUTSIDE = new Set(['02', '15', '60', '66', '69', '72', '78'])

const topo = states as unknown as Topology<{ states: GeometryCollection }>
const lower48 = topo.objects.states.geometries.filter(g => !OUTSIDE.has(String(g.id)))
const land = merge(topo, lower48 as never)
const landFeature = { type: 'Feature' as const, properties: {}, geometry: land }

export const projection: GeoProjection = geoAlbers().fitExtent([[8, 8], [MAP_W - 8, MAP_H - 8]], landFeature)

export const project = (lon: number, lat: number): [number, number] => projection([lon, lat]) ?? [-99, -99]

// Grid points on land (computed once)
export const halftone: [number, number][] = (() => {
  const c = document.createElement('canvas')
  c.width = MAP_W
  c.height = MAP_H
  const ctx = c.getContext('2d')!
  ctx.beginPath()
  geoPath(projection, ctx)(landFeature)
  ctx.fill()
  const px = ctx.getImageData(0, 0, MAP_W, MAP_H).data
  const dots: [number, number][] = []
  for (let y = GRID / 2; y < MAP_H; y += GRID)
    for (let x = GRID / 2; x < MAP_W; x += GRID)
      if (px[(Math.floor(y) * MAP_W + Math.floor(x)) * 4 + 3] > 128) dots.push([x, y])
  return dots
})()

