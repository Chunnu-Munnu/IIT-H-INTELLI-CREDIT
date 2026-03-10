import { create } from 'zustand'

export const useCaseStore = create((set) => ({
    currentCase: null,
    cases: [],
    setCurrentCase: (c) => set({ currentCase: c }),
    setCases: (cases) => set({ cases }),
}))
