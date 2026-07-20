import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
    plugins: [react()],
    build: {
        outDir: 'extension/dist',
        emptyOutDir: false, 
        lib: {
            entry: 'extension/content_script.tsx',
            formats: ['iife'],
            name: 'LiveExplanationContentScript',
            fileName: () => 'content_script.js',
        },
    }
})