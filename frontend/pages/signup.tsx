import { useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { signUp } from '../utils/auth';
import styles from '../styles/Auth.module.css';
import Image from 'next/image';
import logo from '../images/logo-risk.png';

export default function SignUp() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      setLoading(false);
      return;
    }

    const { user, error } = await signUp(email, password);
    
    if (error) {
      setError(error.message || 'Failed to sign up');
      setLoading(false);
      return;
    }

    setSuccess(true);
    setLoading(false);
  };

  if (success) {
    return (
      <div className={styles.container}>
        <div className={styles.formContainer}>
          <h1 className={styles.title}>Verification Required</h1>
          <p>
            We've sent a verification code to your email. Please check your inbox and verify your account.
          </p>
          <div className={styles.links}>
            <Link href="/login">
              Go to Sign In
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.formContainer}>
        <div className={styles.title}>
          <Image src={logo} alt='logo' width={40} height={40} style={{ marginRight: '0.75rem'}} />Risk Assessor
        </div>
        <div className={styles.title2}>Create Account</div>
       
        {error && <div className={styles.error}>{error}</div>}
        
        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.formGroup}>
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className={styles.input}
            />
          </div>
          
          <div className={styles.formGroup}>
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className={styles.input}
              minLength={8}
            />
          </div>
          
          <div className={styles.formGroup}>
            <label htmlFor="confirmPassword">Confirm Password</label>
            <input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              className={styles.input}
              minLength={8}
            />
          </div>
          
          <button 
            type="submit" 
            className={styles.button}
            disabled={loading}
          >
            {loading ? 'Signing up...' : 'Sign Up'}
          </button>
        </form>
        
        <div className={styles.links}>
          <Link href="/login">
            Already have an account? Sign in
          </Link>
        </div>
      </div>
    </div>
  );
}