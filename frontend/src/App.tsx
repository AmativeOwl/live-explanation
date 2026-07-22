import { useEffect, useState } from 'react'

type Explanation = {
  original_text: string,
  explanation: string,
  insight: string,
  jargon_terms: {
    term: string,
    explanation: string,
    confidence: number
  } []
}

function ExplanationCard({ item }: { item: Explanation }) {
  return (
    <div>
      <p style={{ fontSize: '16px', margin: '0 0 8px 0' }}>{item.explanation}</p>
      {item.jargon_terms.length > 0 && (
        <ul style={{ fontSize: '15px', paddingLeft: '20px', margin: 0 }}>
          {item.jargon_terms.map((term) => (
            <li key={term.term} style={{ marginBottom: '6px' }}>
              <strong>{term.term}:</strong> {term.explanation}
            </li>
          ))}
        </ul>
      )}
      {item.insight && (
        <p style={{ fontSize: '15px', margin: '8px 0 0 0', fontStyle: 'italic', color: '#d1d5db' }}>
          💡 {item.insight}
        </p>
      )}
    </div>
  )
}

function App(){
  const [explanations, setExplanations] = useState<Explanation[]>([])
  const [expanded, setExpanded] = useState(false)
  const [collapsed, setCollapsed] = useState(false)

  useEffect(() => {
    const web_socket = new WebSocket('ws://localhost:8000/explanations')

    web_socket.onopen = () => {
      console.log('Connected to backend')
    }

    web_socket.onmessage = (event) => {
      const data: Explanation = JSON.parse(event.data)
      setExplanations((prev) => [...prev, data])
    }

    return () => {
      web_socket.close()
    }
  }, [])

  const latest = explanations[explanations.length - 1]
  const previous = explanations.slice(0, -1).reverse()

  if (collapsed) {
    return (
      <button
        onClick={() => setCollapsed(false)}
        style={{
          fontSize: '14px',
          cursor: 'pointer',
          padding: '8px 12px',
          background: 'none',
          border: 'none',
          color: '#fff',
        }}
      >
        💬 Explanations{explanations.length > 0 ? ` (${explanations.length})` : ''}
      </button>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ fontSize: '20px', margin: '0 0 10px 0' }}>Live Explanations</h1>
        <button
          onClick={() => setCollapsed(true)}
          aria-label="Collapse"
          style={{
            fontSize: '16px',
            cursor: 'pointer',
            background: 'none',
            border: 'none',
            color: '#fff',
            lineHeight: 1,
          }}
        >
          ✕
        </button>
      </div>

      {latest ? (
        <ExplanationCard item={latest} />
      ) : (
        <p style={{ fontSize: '16px' }}>Waiting for the video to say something explainable...</p>
      )}

      {previous.length > 0 && (
        <>
          <button
            onClick={() => setExpanded((prev) => !prev)}
            style={{ fontSize: '14px', margin: '10px 0', cursor: 'pointer' }}
          >
            {expanded ? '▲ Hide previous' : `▼ Show previous (${previous.length})`}
          </button>

          {expanded && (
            <div style={{ borderTop: '1px solid rgba(255,255,255,0.2)', paddingTop: '10px' }}>
              {previous.map((item, index) => (
                <div key={index} style={{ marginBottom: '14px' }}>
                  <ExplanationCard item={item} />
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default App
