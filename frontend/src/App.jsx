import { useState, useEffect } from 'react'
import Plot from 'react-plotly.js'

function App() {
  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [sessionId, setSessionId] = useState(null)
  const [showWelcome, setShowWelcome] = useState(true)
  const [expandedSqlQueries, setExpandedSqlQueries] = useState({})

  // Example questions for suggestion bubbles
  const suggestionQuestions = [
    "What are the top 5 carriers by number of flights?",
    "Show me average delays by month",
    "Which destinations have the most flights from JFK?",
    "What days had the highest number of flights?",
    "Show flights with the longest distance",
    "Compare departure delays across airlines"
  ]

  // Load messages from localStorage on component mount
  useEffect(() => {
    const savedMessages = localStorage.getItem('chatMessages')
    const savedSessionId = localStorage.getItem('sessionId')
    
    if (savedMessages) {
      setMessages(JSON.parse(savedMessages))
      setShowWelcome(false)
    }
    
    if (savedSessionId) {
      setSessionId(savedSessionId)
    }
  }, [])

  // Save messages to localStorage whenever they change
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem('chatMessages', JSON.stringify(messages))
      setShowWelcome(false)
    }
  }, [messages])
  
  // Save sessionId to localStorage whenever it changes
  useEffect(() => {
    if (sessionId) {
      localStorage.setItem('sessionId', sessionId)
    }
  }, [sessionId])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!query.trim()) return
    
    const userMessage = { type: 'user', content: query }
    const currentQuery = query // Store current query
    
    // Clear the input immediately after submission
    setQuery('')
    
    setMessages(prev => [...prev, userMessage])
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch('http://localhost:5001/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          query: currentQuery, // Use stored query value
          session_id: sessionId
        }),
      })
      
      if (!response.ok) {
        throw new Error('Failed to get response')
      }
      
      const data = await response.json()
      
      // Update session ID if provided
      if (data.session_id) {
        setSessionId(data.session_id)
      }
      
      const botMessage = { type: 'bot', content: data }
      setMessages(prev => [...prev, botMessage])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }
  
  const clearChat = () => {
    setMessages([])
    setSessionId(null)
    localStorage.removeItem('chatMessages')
    localStorage.removeItem('sessionId')
    setShowWelcome(true)
    setExpandedSqlQueries({})
  }

  // Handle suggestion click
  const handleSuggestionClick = (suggestion) => {
    setQuery(suggestion)
    // Optional: Auto-submit the form
    // handleSubmit(new Event('submit'))
  }

  // Toggle SQL query visibility
  const toggleSqlQuery = (index) => {
    setExpandedSqlQueries(prev => ({
      ...prev,
      [index]: !prev[index]
    }))
  }

  return (
    <div style={{ 
      maxWidth: '100%', 
      margin: '0', 
      padding: '0', 
      minHeight: '100vh', 
      backgroundColor: '#121212',
      color: 'white'
    }}>
      <div style={{ 
        maxWidth: '1400px', 
        margin: '0 auto', 
        padding: '2rem',
        height: '100vh',
        display: 'flex',
        flexDirection: 'column'
      }}>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          marginBottom: '2rem'
        }}>
          <h1 style={{ fontSize: '2rem', margin: 0 }}>Are you ever just curious about 2013 NYC flight data?</h1>
          {messages.length > 0 && (
            <button 
              onClick={clearChat}
              style={{
                padding: '0.5rem 1rem',
                fontSize: '0.75rem',
                backgroundColor: 'transparent',
                color: '#777',
                border: 'none',
                cursor: 'pointer',
                transition: 'color 0.2s'
              }}
              onMouseOver={(e) => e.target.style.color = '#bbb'}
              onMouseOut={(e) => e.target.style.color = '#777'}
            >
              Clear
            </button>
          )}
        </div>
        
        <div style={{ 
          flex: 1,
          overflowY: 'auto',
          marginBottom: '2rem',
          padding: '1rem',
          backgroundColor: '#121212',
          position: 'relative',
        }}>
          {messages.length === 0 ? (
            <div style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              justifyContent: 'center',
              alignItems: 'center', 
              height: '100%', 
              textAlign: 'center' 
            }}>
              <div style={{ marginBottom: '2rem' }}>
                <p style={{ fontSize: '1.1rem', color: '#aaa', marginBottom: '1rem' }}>
                  This dataset contains information about flights, airlines, airports, 
                  planes, and weather from NYC airports in 2013.
                </p>
                <p style={{ fontSize: '1rem', color: '#888' }}>
                  Try asking a question or select one below:
                </p>
              </div>
              <div style={{ 
                display: 'flex', 
                flexWrap: 'wrap', 
                justifyContent: 'center',
                gap: '1rem',
                maxWidth: '800px'
              }}>
                {suggestionQuestions.map((question, index) => (
                  <button 
                    key={index}
                    onClick={() => handleSuggestionClick(question)}
                    style={{
                      padding: '0.75rem 1rem',
                      backgroundColor: '#1a1a1a',
                      border: '1px solid #333',
                      borderRadius: '2rem',
                      color: '#ddd',
                      fontSize: '0.9rem',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      textAlign: 'center',
                      whiteSpace: 'nowrap'
                    }}
                    onMouseOver={(e) => {
                      e.target.style.backgroundColor = '#292929';
                      e.target.style.borderColor = '#444';
                    }}
                    onMouseOut={(e) => {
                      e.target.style.backgroundColor = '#1a1a1a';
                      e.target.style.borderColor = '#333';
                    }}
                  >
                    {question}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((message, index) => (
              <div 
                key={index} 
                style={{ 
                  marginBottom: message.type === 'user' ? '0.5rem' : '1.5rem',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: message.type === 'user' ? 'flex-end' : 'flex-start',
                }}
              >
                <div style={{
                  maxWidth: '85%',
                  padding: '0.75rem 1rem',
                  color: 'white',
                  backgroundColor: 'transparent',
                }}>
                  {message.type === 'user' ? (
                    <p style={{ margin: 0, fontWeight: '500' }}>{message.content}</p>
                  ) : (
                    <div>
                      {message.content.analysis && (
                        <div style={{ 
                          marginBottom: '1.5rem',
                          padding: '1rem',
                          backgroundColor: '#292929',
                          borderRadius: '8px',
                          borderLeft: '3px solid #636efa'
                        }}>
                          <p style={{ 
                            margin: 0, 
                            color: '#eee',
                            fontSize: '0.95rem',
                            lineHeight: '1.5'
                          }}>
                            {message.content.analysis}
                          </p>
                        </div>
                      )}
                      
                      <div style={{ marginBottom: '1rem' }}>
                        <button 
                          onClick={() => toggleSqlQuery(index)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            width: '100%',
                            padding: '0.5rem 0.75rem',
                            backgroundColor: '#1a1a1a',
                            color: '#ccc',
                            border: 'none',
                            borderRadius: '4px',
                            fontSize: '0.9rem',
                            fontWeight: '500',
                            cursor: 'pointer',
                            textAlign: 'left',
                            transition: 'background-color 0.2s'
                          }}
                          onMouseOver={(e) => {
                            e.target.style.backgroundColor = '#232323';
                          }}
                          onMouseOut={(e) => {
                            e.target.style.backgroundColor = '#1a1a1a';
                          }}
                        >
                          <span>SQL Query</span>
                          <span style={{ fontSize: '0.8rem' }}>
                            {expandedSqlQueries[index] ? '▲' : '▼'}
                          </span>
                        </button>
                        
                        {expandedSqlQueries[index] && (
                          <pre style={{ 
                            padding: '0.75rem',
                            backgroundColor: '#1a1a1a',
                            borderRadius: '0 0 4px 4px',
                            fontSize: '0.85rem',
                            overflowX: 'auto',
                            color: '#ddd',
                            marginTop: '0',
                            borderTop: '1px solid #333'
                          }}>
                            {message.content.sql_query}
                          </pre>
                        )}
                      </div>

                      <div style={{ marginBottom: '1rem' }}>
                        <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem', color: '#ccc' }}>Results</h3>
                        <div style={{ overflowX: 'auto' }}>
                          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                            <thead>
                              <tr>
                                {message.content.data.length > 0 && Object.keys(message.content.data[0] || {}).map((key) => (
                                  <th key={key} style={{ 
                                    padding: '0.5rem',
                                    backgroundColor: '#1a1a1a',
                                    border: '1px solid #444',
                                    textAlign: 'left',
                                    color: '#ddd'
                                  }}>
                                    {key}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {message.content.data.map((row, i) => (
                                <tr key={i}>
                                  {Object.values(row).map((value, j) => (
                                    <td key={j} style={{ 
                                      padding: '0.5rem',
                                      border: '1px solid #444',
                                      color: '#ddd'
                                    }}>
                                      {value}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>

                      {message.content.visualization && (
                        <div>
                          <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem', color: '#ccc' }}>Visualization</h3>
                          <div style={{ width: '100%', height: '300px', backgroundColor: '#1a1a1a', borderRadius: '4px', padding: '10px' }}>
                            <Plot
                              data={message.content.visualization.data}
                              layout={{
                                ...message.content.visualization.layout,
                                margin: { l: 50, r: 20, t: 40, b: 50 },
                                autosize: true,
                                paper_bgcolor: '#1a1a1a',
                                plot_bgcolor: '#1a1a1a',
                                font: { color: '#ddd' },
                                xaxis: { gridcolor: '#444' },
                                yaxis: { gridcolor: '#444' }
                              }}
                              style={{ width: '100%', height: '100%' }}
                              useResizeHandler={true}
                              config={{
                                displayModeBar: false
                              }}
                            />
                          </div>
                        </div>
                      )}
                      
                      {message.content.follow_up_questions && message.content.follow_up_questions.length > 0 && (
                        <div style={{ marginTop: '1.5rem' }}>
                          <h3 style={{ 
                            fontSize: '0.9rem', 
                            marginBottom: '0.75rem', 
                            color: '#aaa',
                            fontWeight: 'normal'
                          }}>
                            Follow-up questions you might be interested in:
                          </h3>
                          <div style={{ 
                            display: 'flex', 
                            flexWrap: 'wrap',
                            gap: '0.5rem',
                            marginBottom: '0.5rem'
                          }}>
                            {message.content.follow_up_questions.map((question, qIndex) => (
                              <button 
                                key={qIndex}
                                onClick={() => handleSuggestionClick(question)}
                                style={{
                                  padding: '0.5rem 1rem',
                                  backgroundColor: 'rgba(99, 110, 250, 0.1)',
                                  border: '1px solid rgba(99, 110, 250, 0.3)',
                                  borderRadius: '2rem',
                                  color: '#b3bbff',
                                  fontSize: '0.85rem',
                                  cursor: 'pointer',
                                  transition: 'all 0.2s',
                                  textAlign: 'center',
                                  whiteSpace: 'nowrap'
                                }}
                                onMouseOver={(e) => {
                                  e.target.style.backgroundColor = 'rgba(99, 110, 250, 0.2)';
                                  e.target.style.borderColor = 'rgba(99, 110, 250, 0.4)';
                                }}
                                onMouseOut={(e) => {
                                  e.target.style.backgroundColor = 'rgba(99, 110, 250, 0.1)';
                                  e.target.style.borderColor = 'rgba(99, 110, 250, 0.3)';
                                }}
                              >
                                {question}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {error && (
          <div style={{ 
            padding: '1rem', 
            marginBottom: '1rem', 
            backgroundColor: '#3d0f0f',
            color: '#ff9999',
            borderRadius: '4px',
            border: '1px solid #662020'
          }}>
            {error}
          </div>
        )}
        
        <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            type="text"
            placeholder="Ask about flight data..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{
              flex: 1,
              padding: '0.75rem',
              fontSize: '1rem',
              backgroundColor: '#1a1a1a',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
            }}
          />
          <button 
            type="submit" 
            disabled={loading}
            style={{
              padding: '0.75rem 1.5rem',
              fontSize: '1rem',
              backgroundColor: '#333',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: loading ? 'not-allowed' : 'pointer'
            }}
          >
            {loading ? 'Loading...' : 'Send'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default App
