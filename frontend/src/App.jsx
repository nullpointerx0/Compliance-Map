import React from 'react'

function App() {
  return (
    <div className="min-h-screen bg-darkBg text-gray-100 flex flex-col items-center justify-center p-6">
      <h1 className="text-4xl font-extrabold text-brandPrimary mb-4">
        Ghost Kitchen Compliance Map
      </h1>
      <p className="text-gray-400 text-lg mb-8 max-w-md text-center">
        Project phase 1 scaffold is successfully initialized. React, Vite, and Tailwind CSS v3 are running.
      </p>
      <div className="flex gap-4">
        <span className="px-4 py-2 rounded bg-darkCard border border-darkBorder text-sm text-gray-300">
          React 19
        </span>
        <span className="px-4 py-2 rounded bg-darkCard border border-darkBorder text-sm text-gray-300">
          Vite
        </span>
        <span className="px-4 py-2 rounded bg-darkCard border border-darkBorder text-sm text-gray-300">
          Tailwind CSS v3
        </span>
      </div>
    </div>
  )
}

export default App
