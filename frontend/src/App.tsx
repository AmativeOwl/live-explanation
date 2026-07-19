import { useEffect, useState } from 'react'

type Explanation = {
  original_text: string,
  explanation: string,
  jargon_terms: {
    term: string,
    explanation: string,
    confidence: number
  } []
}

function App(){
  const [explanations, setExplanations] = useState<Explanation[]>([])

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

  return (
    <div>
      <h1>Live Explanations</h1>
      {explanations.map((item, index) => (
        <div key = {index}>
          <p><strong>Explanation:</strong> {item.explanation}</p>
          {item.jargon_terms.length > 0 && (
            <ul>
              {item.jargon_terms.map((term) => (
                <li key = {term.term}>
                  <strong>{term.term}:</strong> {term.explanation}
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
      <p>Explanations received: {explanations.length}</p>
    </div>
  )
}

export default App
