'use client'

import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import { Upload, FileText, CheckCircle, XCircle, Loader2, Settings, X, Moon, Sun, Award, Download, Play, Zap } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const API_URL = 'http://localhost:8000'

export default function Home() {
  const [step, setStep] = useState(1)
  const [jdText, setJdText] = useState('')
  const [rubric, setRubric] = useState('')
  const [resumeText, setResumeText] = useState('')
  const [evaluation, setEvaluation] = useState<any>(null)
  const [githubUrl, setGithubUrl] = useState('')
  const [githubAnalysis, setGithubAnalysis] = useState<any>(null)
  const [finalVerdict, setFinalVerdict] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showSettings, setShowSettings] = useState(false)
  const [thresholds, setThresholds] = useState({ level_1: 7.0, level_2: 6.0, level_3: 8.0 })
  const [darkMode, setDarkMode] = useState(false)
  const jdFileInputRef = useRef<HTMLInputElement>(null)
  const resumeFileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    // Load dark mode preference from localStorage
    const savedTheme = localStorage.getItem('darkMode')
    if (savedTheme) {
      setDarkMode(savedTheme === 'true')
    }
  }, [])

  useEffect(() => {
    // Save dark mode preference
    localStorage.setItem('darkMode', darkMode.toString())
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [darkMode])

  const fetchThresholds = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/v1/config/thresholds`)
      setThresholds(res.data.data)
    } catch (err) {
      console.error('Failed to fetch thresholds', err)
    }
  }

  const updateThresholds = async () => {
    try {
      await axios.post(`${API_URL}/api/v1/config/thresholds`, null, {
        params: thresholds
      })
      setShowSettings(false)
      alert('Thresholds updated successfully!')
    } catch (err: any) {
      alert('Failed to update thresholds: ' + (err.response?.data?.detail || err.message))
    }
  }

  const uploadJD = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await axios.post(`${API_URL}/api/v1/jd/upload-text`, {
        jd_text: jdText
      })
      
      // Generate rubric
      const rubricRes = await axios.post(`${API_URL}/api/v1/rubric/generate`)
      setRubric(rubricRes.data.data.rubric)
      setStep(2)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to process JD')
    }
    setLoading(false)
  }

  const uploadJDFile = async (file: File) => {
    setLoading(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('file', file)
      
      const res = await axios.post(`${API_URL}/api/v1/jd/upload-file`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      
      // Generate rubric
      const rubricRes = await axios.post(`${API_URL}/api/v1/rubric/generate`)
      setRubric(rubricRes.data.data.rubric)
      setStep(2)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to process JD file')
    }
    setLoading(false)
  }

  const handleJDFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      uploadJDFile(file)
    }
  }

  const evaluateResume = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await axios.post(`${API_URL}/api/v1/resume/evaluate-text`, {
        resume_text: resumeText
      })
      setEvaluation(res.data.data)
      
      // Auto-fill GitHub URL if found in resume
      if (res.data.data.github_url) {
        setGithubUrl(res.data.data.github_url)
      }
      
      // Always proceed to GitHub analysis for comprehensive evaluation
      setStep(3) // Go to GitHub input
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to evaluate resume')
    }
    setLoading(false)
  }

  const evaluateResumeFile = async (file: File) => {
    setLoading(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('file', file)
      
      const res = await axios.post(`${API_URL}/api/v1/resume/evaluate-file`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setEvaluation(res.data.data)
      
      // Auto-fill GitHub URL if found in resume
      if (res.data.data.github_url) {
        setGithubUrl(res.data.data.github_url)
      }
      
      // Always proceed to GitHub analysis for comprehensive evaluation
      setStep(3) // Go to GitHub input
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to evaluate resume file')
    }
    setLoading(false)
  }

  const handleResumeFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      evaluateResumeFile(file)
    }
  }

  const analyzeGitHub = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await axios.post(`${API_URL}/api/v1/github/analyze`, {
        github_url: githubUrl
      })
      setGithubAnalysis(res.data.data)
      setStep(4) // Go to results display
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to analyze GitHub')
    }
    setLoading(false)
  }

  const generateFinalVerdict = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await axios.post(`${API_URL}/api/v1/verdict/generate`)
      setFinalVerdict(res.data.data)
      setStep(5) // Go to final verdict
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate final verdict')
    }
    setLoading(false)
  }

  const downloadPDF = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/export/pdf`, {
        responseType: 'blob'
      })
      
      // Create blob link to download
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `candidate_evaluation_${Date.now()}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.parentNode?.removeChild(link)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to download PDF')
    }
  }

  return (
    <main className={`min-h-screen p-8 transition-colors ${darkMode ? 'bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900' : 'bg-gradient-to-br from-blue-50 via-white to-purple-50'}`}>
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12 relative">
          <div className="absolute right-0 top-0 flex gap-3">
            <button
              onClick={() => setDarkMode(!darkMode)}
              className={`p-3 rounded-full shadow-lg hover:shadow-xl transition-all ${darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-white hover:bg-gray-50'}`}
              title={darkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
            >
              {darkMode ? <Sun className="w-6 h-6 text-yellow-400" /> : <Moon className="w-6 h-6 text-gray-700" />}
            </button>
            <button
              onClick={() => {
                fetchThresholds()
                setShowSettings(true)
              }}
              className={`p-3 rounded-full shadow-lg hover:shadow-xl transition-all ${darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-white hover:bg-gray-50'}`}
              title="Configure Thresholds"
            >
              <Settings className={`w-6 h-6 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`} />
            </button>
          </div>
          
          <h1 className="text-5xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2 leading-tight">
            Tech Hiring AI
          </h1>
          <p className={`text-lg leading-relaxed ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
            Powered by Google ADK • Intelligent Candidate Evaluation
          </p>
        </div>

        {/* Progress Steps */}
        <div className="flex items-center justify-between mb-12 w-full max-w-4xl mx-auto">
          {[
            { num: 1, label: 'JD' },
            { num: 2, label: 'Resume' },
            { num: 3, label: 'GitHub' },
            { num: 4, label: 'Results' },
            { num: 5, label: 'Verdict' }
          ].map((s, idx) => (
            <div key={s.num} className="flex items-center" style={{ flex: idx < 4 ? '1' : '0 0 auto' }}>
              <div className="flex flex-col items-center">
                <div className={`w-12 h-12 rounded-full flex items-center justify-center font-bold text-lg transition-colors
                  ${step >= s.num 
                    ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg' 
                    : darkMode ? 'bg-gray-700 text-gray-400' : 'bg-gray-200 text-gray-500'}`}>
                  {s.num}
                </div>
                <span className={`text-xs mt-1 font-medium ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>{s.label}</span>
              </div>
              {idx < 4 && <div className={`h-1 mx-3 transition-colors ${step > s.num ? 'bg-gradient-to-r from-blue-600 to-purple-600' : darkMode ? 'bg-gray-700' : 'bg-gray-200'}`} style={{ flex: 1, minWidth: '60px' }} />}
            </div>
          ))}
        </div>

        {/* Step 1: Job Description */}
        {step === 1 && (
          <div className={`rounded-2xl shadow-xl p-8 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
            <div className="flex items-center mb-6">
              <FileText className="w-8 h-8 text-blue-600 mr-3" />
              <h2 className={`text-3xl font-bold ${darkMode ? 'text-white' : 'text-gray-800'}`}>Step 1: Job Description</h2>
            </div>
            
            <textarea
              className={`w-full h-64 p-4 border-2 rounded-lg focus:border-blue-500 focus:outline-none resize-none ${darkMode ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'bg-white border-gray-200 text-gray-800 placeholder-gray-400'}`}
              placeholder="Paste your job description here...&#10;&#10;Example:&#10;Senior Python Developer&#10;&#10;Requirements:&#10;- 5+ years Python experience&#10;- Django/Flask&#10;- PostgreSQL&#10;- Docker"
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
            />

            {error && (
              <div className={`mt-4 p-4 border rounded-lg ${darkMode ? 'bg-red-900/30 border-red-700 text-red-300' : 'bg-red-50 border-red-200 text-red-700'}`}>
                {error}
              </div>
            )}

            <div className="flex gap-4 mt-6">
              <button
                onClick={uploadJD}
                disabled={!jdText || loading}
                className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600 text-white py-4 rounded-lg font-semibold text-lg hover:from-blue-700 hover:to-purple-700 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed transition-all flex items-center justify-center shadow-lg"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-6 h-6 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Play className="w-6 h-6 mr-2" />
                    Process Text
                  </>
                )}
              </button>
              
              <input
                ref={jdFileInputRef}
                type="file"
                accept=".txt,.pdf"
                onChange={handleJDFileChange}
                className="hidden"
              />
              <button
                onClick={() => jdFileInputRef.current?.click()}
                disabled={loading}
                className={`flex-1 py-4 rounded-lg font-semibold text-lg transition-all flex items-center justify-center shadow-lg ${darkMode ? 'bg-gray-700 text-white hover:bg-gray-600' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'} disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                <Upload className="w-6 h-6 mr-2" />
                Upload File (PDF/TXT)
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Resume Upload */}
        {step === 2 && (
          <div className="space-y-6">
            {/* Rubric Display */}
            <div className={`rounded-2xl shadow-xl p-8 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
              <h3 className={`text-2xl font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-800'}`}>Generated Rubric</h3>
              <div className={`p-6 rounded-lg prose prose-sm max-w-none ${darkMode ? 'bg-gray-700/50 prose-invert' : 'bg-gray-50'}`}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{rubric}</ReactMarkdown>
              </div>
            </div>

            {/* Resume Input */}
            <div className={`rounded-2xl shadow-xl p-8 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
              <div className="flex items-center mb-6">
                <Upload className="w-8 h-8 text-purple-600 mr-3" />
                <h2 className={`text-3xl font-bold ${darkMode ? 'text-white' : 'text-gray-800'}`}>Step 2: Candidate Resume</h2>
              </div>
              
              <textarea
                className={`w-full h-64 p-4 border-2 rounded-lg focus:border-purple-500 focus:outline-none resize-none ${darkMode ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'bg-white border-gray-200 text-gray-800 placeholder-gray-400'}`}
                placeholder="Paste candidate's resume here...&#10;&#10;Example:&#10;John Doe&#10;Email: john@example.com&#10;&#10;Experience:&#10;- Senior Python Developer at TechCorp (6 years)&#10;- Django, Flask, PostgreSQL&#10;- Docker, Kubernetes"
                value={resumeText}
                onChange={(e) => setResumeText(e.target.value)}
              />

              {error && (
                <div className={`mt-4 p-4 border rounded-lg ${darkMode ? 'bg-red-900/30 border-red-700 text-red-300' : 'bg-red-50 border-red-200 text-red-700'}`}>
                  {error}
                </div>
              )}

              <div className="flex gap-4 mt-6">
                <button
                  onClick={() => setStep(1)}
                  className={`flex-1 py-4 rounded-lg font-semibold text-lg transition-colors ${darkMode ? 'bg-gray-700 text-white hover:bg-gray-600' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
                >
                  Back to JD
                </button>
                <button
                  onClick={evaluateResume}
                  disabled={!resumeText || loading}
                  className="flex-1 bg-gradient-to-r from-purple-600 to-pink-600 text-white py-4 rounded-lg font-semibold text-lg hover:from-purple-700 hover:to-pink-700 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed transition-all flex items-center justify-center shadow-lg"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-6 h-6 mr-2 animate-spin" />
                      Evaluating...
                    </>
                  ) : (
                    <>
                      <Zap className="w-5 h-5 mr-2" />
                      Evaluate Text
                    </>
                  )}
                </button>
                <input
                  ref={resumeFileInputRef}
                  type="file"
                  accept=".txt,.pdf"
                  onChange={handleResumeFileChange}
                  className="hidden"
                />
                <button
                  onClick={() => resumeFileInputRef.current?.click()}
                  disabled={loading}
                  className={`flex-1 py-4 rounded-lg font-semibold text-lg transition-all flex items-center justify-center shadow-lg ${darkMode ? 'bg-gray-700 text-white hover:bg-gray-600' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'} disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  <Upload className="w-5 h-5 mr-2" />
                  Upload File
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Step 3: GitHub Analysis */}
        {step === 3 && evaluation && (
          <div className={`rounded-2xl shadow-xl p-8 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
            <div className="flex items-center mb-6">
              {evaluation.passed ? (
                <CheckCircle className="w-8 h-8 text-green-600 mr-3" />
              ) : (
                <XCircle className="w-8 h-8 text-orange-600 mr-3" />
              )}
              <h2 className={`text-3xl font-bold ${darkMode ? 'text-white' : 'text-gray-800'}`}>
                {evaluation.passed ? 'Level 1 Passed! ' : 'Level 1 Complete - '}Enter GitHub Profile
              </h2>
            </div>

            <div className={`border rounded-lg p-4 mb-6 ${
              evaluation.passed 
                ? (darkMode ? 'bg-green-900/30 border-green-700' : 'bg-green-50 border-green-200')
                : (darkMode ? 'bg-orange-900/30 border-orange-700' : 'bg-orange-50 border-orange-200')
            }`}>
              <p className={evaluation.passed ? (darkMode ? 'text-green-300' : 'text-green-800') : (darkMode ? 'text-orange-300' : 'text-orange-800')}>
                <strong>Level 1 Score: {evaluation.score}/{evaluation.max_score}</strong> - {evaluation.passed ? 'Passed!' : `Below threshold (${evaluation.threshold}). Continuing with comprehensive evaluation.`}
              </p>
            </div>

            {evaluation.github_url && (
              <div className={`border rounded-lg p-4 mb-4 flex items-start ${darkMode ? 'bg-blue-900/30 border-blue-700' : 'bg-blue-50 border-blue-200'}`}>
                <CheckCircle className="w-5 h-5 text-blue-600 mr-2 mt-0.5 flex-shrink-0" />
                <div>
                  <p className={`font-semibold ${darkMode ? 'text-blue-300' : 'text-blue-800'}`}>GitHub profile auto-detected from resume!</p>
                  <p className={`text-sm ${darkMode ? 'text-blue-400' : 'text-blue-600'}`}>You can edit or confirm the username below.</p>
                </div>
              </div>
            )}

            <label className={`block font-semibold mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              GitHub Profile URL or Username {!githubUrl && <span className="text-red-500">*</span>}
            </label>
            <input
              type="text"
              className={`w-full p-4 border-2 rounded-lg focus:border-green-500 focus:outline-none ${darkMode ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'bg-white border-gray-200 text-gray-800 placeholder-gray-400'}`}
              placeholder={githubUrl ? githubUrl : "Enter GitHub username (e.g., 'torvalds' or 'https://github.com/torvalds')"}
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
            />
            <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              {!githubUrl 
                ? "⚠️ Please enter a GitHub username to proceed with Level 2 analysis, or skip to view Level 1 results only."
                : "✓ Ready to analyze! Click 'Analyze GitHub' below."}
            </p>

            {error && (
              <div className={`mt-4 p-4 border rounded-lg ${darkMode ? 'bg-red-900/30 border-red-700 text-red-300' : 'bg-red-50 border-red-200 text-red-700'}`}>
                {error}
              </div>
            )}

            <div className="flex gap-4 mt-6">
              <button
                onClick={() => setStep(2)}
                className={`flex-1 py-4 rounded-lg font-semibold text-lg transition-colors ${darkMode ? 'bg-gray-700 text-white hover:bg-gray-600' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
              >
                Back
              </button>
              <button
                onClick={() => setStep(4)}
                className="flex-1 bg-yellow-600 text-white py-4 rounded-lg font-semibold text-lg hover:bg-yellow-700 transition-colors"
              >
                Skip Level 2
              </button>
              <button
                onClick={analyzeGitHub}
                disabled={!githubUrl || loading}
                className="flex-1 bg-gradient-to-r from-green-600 to-emerald-600 text-white py-4 rounded-lg font-semibold text-lg hover:from-green-700 hover:to-emerald-700 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed transition-all flex items-center justify-center shadow-lg"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-6 h-6 mr-2 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  'Analyze GitHub'
                )}
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Results */}
        {step === 4 && evaluation && (
          <div className={`rounded-2xl shadow-xl p-8 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
            <div className="text-center mb-8">
              {evaluation.passed ? (
                <CheckCircle className="w-20 h-20 text-green-500 mx-auto mb-4" />
              ) : (
                <XCircle className="w-20 h-20 text-red-500 mx-auto mb-4" />
              )}
              <h2 className={`text-4xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-800'}`}>
                {evaluation.passed ? 'Candidate Passed!' : 'Candidate Did Not Pass'}
              </h2>
              <div className="text-6xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                {evaluation.score}/{evaluation.max_score}
              </div>
              <p className={`mt-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                Threshold: {evaluation.threshold}/10
              </p>
            </div>

            <div className="space-y-6">
              {/* Level 1 Results */}
              <div className={`border-2 rounded-lg p-6 ${darkMode ? 'bg-blue-900/30 border-blue-700' : 'bg-blue-50 border-blue-200'}`}>
                <h3 className={`text-xl font-bold mb-3 ${darkMode ? 'text-blue-300' : 'text-blue-800'}`}>📄 Level 1: Resume Evaluation</h3>
                <div className={`text-3xl font-bold mb-2 ${darkMode ? 'text-blue-400' : 'text-blue-600'}`}>
                  {evaluation.score}/{evaluation.max_score}
                </div>
                <div className={`prose prose-sm max-w-none ${darkMode ? 'prose-invert' : 'text-gray-700'}`}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{evaluation.evaluation}</ReactMarkdown>
                </div>
              </div>

              {/* Level 2 Results */}
              {githubAnalysis && (
                <div className={`border-2 rounded-lg p-6 ${darkMode ? 'bg-green-900/30 border-green-700' : 'bg-green-50 border-green-200'}`}>
                  <h3 className={`text-xl font-bold mb-3 ${darkMode ? 'text-green-300' : 'text-green-800'}`}>💻 Level 2: GitHub Analysis</h3>
                  <div className="mb-4">
                    <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>GitHub: <strong>{githubAnalysis.github_url}</strong></p>
                    <div className={`text-3xl font-bold mt-2 ${darkMode ? 'text-green-400' : 'text-green-600'}`}>
                      {githubAnalysis.score}/{githubAnalysis.max_score}
                    </div>
                    <p className={`text-sm font-semibold ${githubAnalysis.passed ? 'text-green-600' : 'text-red-600'}`}>
                      {githubAnalysis.passed ? '✓ PASSED' : '✗ FAILED'} (Threshold: {githubAnalysis.threshold}/10)
                    </p>
                  </div>
                  <div className={`prose prose-sm max-w-none ${darkMode ? 'prose-invert' : 'text-gray-700'}`}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{githubAnalysis.analysis}</ReactMarkdown>
                  </div>
                </div>
              )}

              <div className="space-y-4">
                {/* Download PDF Button */}
                <button
                  onClick={downloadPDF}
                  className="w-full bg-gradient-to-r from-indigo-600 to-blue-600 text-white py-4 rounded-lg font-semibold text-lg hover:from-indigo-700 hover:to-blue-700 transition-all flex items-center justify-center shadow-lg"
                >
                  <Download className="w-6 h-6 mr-2" />
                  Download PDF Report
                </button>

                <div className="flex gap-4">
                  {/* Show Generate Verdict button if both L1 and L2 are complete and verdict not generated yet */}
                  {githubAnalysis && !finalVerdict && (
                    <button
                      onClick={generateFinalVerdict}
                      disabled={loading}
                      className="flex-1 bg-gradient-to-r from-green-600 to-emerald-600 text-white py-4 rounded-lg font-semibold text-lg hover:from-green-700 hover:to-emerald-700 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed transition-all flex items-center justify-center shadow-lg"
                    >
                      {loading ? (
                        <>
                          <Loader2 className="w-6 h-6 mr-2 animate-spin" />
                          Generating...
                        </>
                      ) : (
                        <>
                          <Award className="w-6 h-6 mr-2" />
                          Generate Final Verdict
                        </>
                      )}
                    </button>
                  )}
                  {/* Show View Verdict button if verdict has been generated */}
                  {finalVerdict && (
                    <button
                      onClick={() => setStep(5)}
                      className="flex-1 bg-gradient-to-r from-purple-600 to-indigo-600 text-white py-4 rounded-lg font-semibold text-lg hover:from-purple-700 hover:to-indigo-700 transition-all flex items-center justify-center shadow-lg"
                    >
                      <Award className="w-6 h-6 mr-2" />
                      View Final Verdict
                    </button>
                  )}
                  <button
                    onClick={() => {
                      setStep(2)
                      setResumeText('')
                      setGithubUrl('')
                      setEvaluation(null)
                      setGithubAnalysis(null)
                      setFinalVerdict(null)
                    }}
                    className="flex-1 bg-blue-600 text-white py-4 rounded-lg font-semibold text-lg hover:bg-blue-700 transition-colors"
                  >
                    Evaluate Another Candidate
                  </button>
                  <button
                    onClick={() => {
                      setStep(1)
                      setJdText('')
                      setRubric('')
                      setResumeText('')
                      setGithubUrl('')
                      setEvaluation(null)
                      setGithubAnalysis(null)
                      setFinalVerdict(null)
                    }}
                    className={`flex-1 py-4 rounded-lg font-semibold text-lg transition-colors ${darkMode ? 'bg-gray-700 text-white hover:bg-gray-600' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
                  >
                    Start Over
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 5: Final Verdict */}
        {step === 5 && finalVerdict && (
          <div className={`rounded-2xl shadow-2xl p-8 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
            <div className="text-center mb-8">
              <Award className={`w-24 h-24 mx-auto mb-4 ${finalVerdict.decision === 'HIRE' ? 'text-green-500' : 'text-red-500'}`} />
              <h2 className={`text-5xl font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-800'}`}>
                Final Verdict
              </h2>
              <div className={`inline-block px-8 py-4 rounded-2xl text-4xl font-bold mb-4 ${
                finalVerdict.decision === 'HIRE' 
                  ? 'bg-gradient-to-r from-green-500 to-emerald-500 text-white shadow-lg' 
                  : 'bg-gradient-to-r from-red-500 to-rose-500 text-white shadow-lg'
              }`}>
                {finalVerdict.decision === 'HIRE' ? '✅ HIRE' : '❌ NO HIRE'}
              </div>
              <div className={`mt-4 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                <p className="text-xl">Confidence: <strong>{finalVerdict.confidence}</strong></p>
                <p className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mt-2">
                  Composite Score: {finalVerdict.composite_score}/10
                </p>
              </div>
            </div>

            {/* Score Breakdown */}
            <div className={`grid grid-cols-1 md:grid-cols-2 gap-4 mb-8 ${darkMode ? 'text-white' : 'text-gray-800'}`}>
              <div className={`p-6 rounded-xl border-2 ${darkMode ? 'bg-gray-700/50 border-blue-500/30' : 'bg-blue-50 border-blue-200'}`}>
                <h3 className="text-lg font-semibold mb-2">📄 Level 1: Resume</h3>
                <div className="text-3xl font-bold text-blue-600">{finalVerdict.level_1_score}/10</div>
              </div>
              <div className={`p-6 rounded-xl border-2 ${darkMode ? 'bg-gray-700/50 border-green-500/30' : 'bg-green-50 border-green-200'}`}>
                <h3 className="text-lg font-semibold mb-2">💻 Level 2: GitHub</h3>
                <div className="text-3xl font-bold text-green-600">{finalVerdict.level_2_score}/10</div>
              </div>
              {finalVerdict.level_3_score !== null && (
                <div className={`p-6 rounded-xl border-2 col-span-2 ${darkMode ? 'bg-gray-700/50 border-purple-500/30' : 'bg-purple-50 border-purple-200'}`}>
                  <h3 className="text-lg font-semibold mb-2">⚡ Level 3: Coding</h3>
                  <div className="text-3xl font-bold text-purple-600">{finalVerdict.level_3_score}/10</div>
                </div>
              )}
            </div>

            {/* Detailed Verdict */}
            <div className={`rounded-xl p-6 mb-6 ${darkMode ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
              <h3 className={`text-2xl font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-800'}`}>📋 Detailed Analysis</h3>
              <div className={`prose prose-sm max-w-none ${darkMode ? 'prose-invert' : ''}`}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{finalVerdict.verdict_text}</ReactMarkdown>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="space-y-4">
              {/* Download PDF Button */}
              <button
                onClick={downloadPDF}
                className="w-full bg-gradient-to-r from-indigo-600 to-blue-600 text-white py-4 rounded-lg font-semibold text-lg hover:from-indigo-700 hover:to-blue-700 transition-all flex items-center justify-center shadow-lg"
              >
                <Download className="w-6 h-6 mr-2" />
                Download Complete Report (PDF)
              </button>

              <div className="flex gap-4">
                <button
                  onClick={() => setStep(4)}
                  className={`flex-1 py-4 rounded-lg font-semibold text-lg transition-colors ${darkMode ? 'bg-gray-700 text-white hover:bg-gray-600' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
                >
                  Back to Results
                </button>
                <button
                  onClick={() => {
                    setStep(2)
                    setResumeText('')
                    setGithubUrl('')
                    setEvaluation(null)
                    setGithubAnalysis(null)
                    setFinalVerdict(null)
                  }}
                  className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600 text-white py-4 rounded-lg font-semibold text-lg hover:from-blue-700 hover:to-purple-700 transition-all shadow-lg"
                >
                  Evaluate Another Candidate
                </button>
                <button
                  onClick={() => {
                    setStep(1)
                    setJdText('')
                    setRubric('')
                    setResumeText('')
                    setGithubUrl('')
                    setEvaluation(null)
                    setGithubAnalysis(null)
                    setFinalVerdict(null)
                  }}
                  className={`flex-1 py-4 rounded-lg font-semibold text-lg transition-colors ${darkMode ? 'bg-gray-700 text-white hover:bg-gray-600' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
                >
                  Start Over
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Settings Modal */}
        {showSettings && (
          <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
            <div className={`rounded-2xl shadow-2xl max-w-md w-full p-8 relative ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
              <button
                onClick={() => setShowSettings(false)}
                className={`absolute right-4 top-4 p-2 rounded-full transition-colors ${darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}
              >
                <X className={`w-5 h-5 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`} />
              </button>

              <h2 className={`text-2xl font-bold mb-6 ${darkMode ? 'text-white' : 'text-gray-800'}`}>
                Configure Thresholds
              </h2>

              <div className="space-y-6">
                {/* Level 1 Threshold */}
                <div>
                  <label className={`block text-sm font-semibold mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    Level 1 Threshold (Resume vs JD)
                  </label>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="0"
                      max="10"
                      step="0.5"
                      value={thresholds.level_1}
                      onChange={(e) => setThresholds({...thresholds, level_1: parseFloat(e.target.value)})}
                      className="flex-1 h-2 bg-blue-200 rounded-lg appearance-none cursor-pointer"
                    />
                    <input
                      type="number"
                      min="0"
                      max="10"
                      step="0.5"
                      value={thresholds.level_1}
                      onChange={(e) => setThresholds({...thresholds, level_1: parseFloat(e.target.value)})}
                      className={`w-20 px-3 py-2 border-2 rounded-lg text-center font-bold ${darkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300 text-gray-800'}`}
                    />
                  </div>
                  <p className={`text-xs mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>Default: 7.0/10</p>
                </div>

                {/* Level 2 Threshold */}
                <div>
                  <label className={`block text-sm font-semibold mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    Level 2 Threshold (GitHub Analysis)
                  </label>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="0"
                      max="10"
                      step="0.5"
                      value={thresholds.level_2}
                      onChange={(e) => setThresholds({...thresholds, level_2: parseFloat(e.target.value)})}
                      className="flex-1 h-2 bg-purple-200 rounded-lg appearance-none cursor-pointer"
                    />
                    <input
                      type="number"
                      min="0"
                      max="10"
                      step="0.5"
                      value={thresholds.level_2}
                      onChange={(e) => setThresholds({...thresholds, level_2: parseFloat(e.target.value)})}
                      className={`w-20 px-3 py-2 border-2 rounded-lg text-center font-bold ${darkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300 text-gray-800'}`}
                    />
                  </div>
                  <p className={`text-xs mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>Default: 6.0/10</p>
                </div>

                {/* Level 3 Threshold */}
                <div>
                  <label className={`block text-sm font-semibold mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    Level 3 Threshold (Overall Assessment)
                  </label>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="0"
                      max="10"
                      step="0.5"
                      value={thresholds.level_3}
                      onChange={(e) => setThresholds({...thresholds, level_3: parseFloat(e.target.value)})}
                      className="flex-1 h-2 bg-green-200 rounded-lg appearance-none cursor-pointer"
                    />
                    <input
                      type="number"
                      min="0"
                      max="10"
                      step="0.5"
                      value={thresholds.level_3}
                      onChange={(e) => setThresholds({...thresholds, level_3: parseFloat(e.target.value)})}
                      className={`w-20 px-3 py-2 border-2 rounded-lg text-center font-bold ${darkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300 text-gray-800'}`}
                    />
                  </div>
                  <p className={`text-xs mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>Default: 8.0/10</p>
                </div>
              </div>

              <div className="flex gap-3 mt-8">
                <button
                  onClick={() => setShowSettings(false)}
                  className={`flex-1 py-3 rounded-lg font-semibold transition-colors ${darkMode ? 'bg-gray-700 text-white hover:bg-gray-600' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
                >
                  Cancel
                </button>
                <button
                  onClick={updateThresholds}
                  className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3 rounded-lg font-semibold hover:from-blue-700 hover:to-purple-700 transition-colors shadow-lg"
                >
                  Save Changes
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  )
}
