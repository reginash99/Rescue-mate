import { defineStore } from 'pinia'

export const useMapStore = defineStore('map', {
  state: () => ({ features: [] as any[] }),
  actions: {
    setFeatures(fc: any) { this.features = fc?.features ?? [] }
  }
})
