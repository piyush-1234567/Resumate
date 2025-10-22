import React, { useState } from 'react';
import './App.css'; // We'll update this next

function App() {
  // State for loading messages and the final results
  const [message, setMessage] = useState("Click the button to check for new resumes.");
  const [applicants, setApplicants] = useState([]); // Will hold the list of applicants

  // This function is called when the button is clicked
  const handleProcessEmails = () => {
    setMessage("Processing... 🤖 This may take a moment.");
    setApplicants([]); // Clear old results

    // Call the new backend route
    fetch("http://localhost:5000/process-emails")
      .then(res => res.json())
      .then(data => {
        if (data.error) {
          setMessage(data.error);
        } else if (data.processed_applicants && data.processed_applicants.length > 0) {
          // Success! We found applicants.
          setMessage(`Success! Processed ${data.processed_applicants.length} new applicant(s).`);
          setApplicants(data.processed_applicants);
        } else {
          // Success, but no new emails were found
          setMessage("No new resumes found in the inbox.");
        }
      })
      .catch(err => {
        console.error(err);
        setMessage("An error occurred. Is the backend server running?");
      });
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Resumate Automated Pipeline</h1>
        
        <div className="controls-container">
          <button onClick={handleProcessEmails}>
            Process New Resumes
          </button>
        </div>
        
        <h3>{message}</h3>

        {/* --- Results Area --- */}
        <div className="results-dashboard">
          {applicants.map((applicant, index) => (
            <div key={index} className="applicant-card">
              <h3>{applicant.sender}</h3>
              <p className="applicant-score">Score: {applicant.score}%</p>
              <p>File: {applicant.filename}</p>
              
              <div className="keyword-container">
                <h4>Matched Keywords:</h4>
                <ul className="keywords-list">
                  {applicant.matched.length > 0 ? (
                    applicant.matched.map((kw, i) => (
                      <li key={i} className="keyword-match">{kw}</li>
                    ))
                  ) : (
                    <p>None</p>
                  )}
                </ul>
              </div>

              <div className="keyword-container">
                <h4>Missing Keywords:</h4>
                <ul className="keywords-list">
                  {applicant.missing.length > 0 ? (
                    applicant.missing.map((kw, i) => (
                      <li key={i} className="keyword-missing">{kw}</li>
                    ))
                  ) : (
                    <p>None</p>
                  )}
                </ul>
              </div>
            </div>
          ))}
        </div>
        
      </header>
    </div>
  );
}

export default App;