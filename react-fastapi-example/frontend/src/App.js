import React, { useEffect, useState } from "react";

function App() {
  const [data, setData] = useState([]);

  useEffect(() => {
    fetch(`${process.env.REACT_APP_BACKEND_URL || window.location.href}/data`)
      .then((response) => response.json())
      .then((data) => setData(data.data))
      .catch((error) => console.error("Error fetching data:", error));
  }, []);

  return (
    <div className="App">
      <h1>React + FastAPI Example</h1>
      <ul>
        {data.map((item, index) => (
          <li key={index}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export default App;
 