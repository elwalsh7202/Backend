import React, {useState} from "react"

const Login = (props) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    console.log(username);

  }

    return (
      <div>
        <form className="Login" form onSubmit={handleSubmit}>
          <label htmlFor="username">Username</label>
          <input value={username} onChange={(e) => setUsername(e.target.value)} type="username" placeholder="Username" id="username" name="email"/>
          <label htmlFor="password">Password</label>
          <input value ={password} onChange={(e) => setPassword(e.target.value)} type="password" placeholder="************" id="password" name="password"/>
          <button type="submit">Log In</button>
      </form>
      </div>
     
    )
  }
  
  
  
  export default Login