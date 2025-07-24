import { useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { signIn, signInWithFederatedSSO } from '../utils/auth';
import styles from '../styles/Auth.module.css';
import Image from 'next/image';
import logo from '../images/logo-risk.png';

const federatedSsoEnabled = process.env.NEXT_PUBLIC_FEDERATED_SSO_ENABLED === 'true';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [authMethod, setAuthMethod] = useState<'select' | 'password'>(federatedSsoEnabled ? 'select' : 'password');
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const { user, error } = await signIn(email, password);
    
    if (error) {
      setError(error.message || 'Failed to sign in');
      setLoading(false);
      return;
    }

    router.push('/');
  };

  // Auth method selection screen
  if (authMethod === 'select') {
    return (
      <div className={styles.container}>
        <div className={styles.formContainer}>
          <div className={styles.title}>
            <Image src={logo} alt='logo' width={40} height={40} style={{ marginRight: '0.75rem'}} />Risk Assessor
          </div>
          <div className={styles.title2}>Sign In</div>

          <div className={styles.form}>
            <button className={styles.ssoButton} onClick={signInWithFederatedSSO}>
              Sign in with SSO
            </button>

            <div className={styles.divider}>
              <span>OR</span>
            </div>

            <button className={styles.button} onClick={() => setAuthMethod('password')}>
              Sign in with Email &amp; Password
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Email/password form
  return (
    <div className={styles.container}>
      <div className={styles.formContainer}>
        <div className={styles.title}>
          <Image src={logo} alt='logo' width={40} height={40} style={{ marginRight: '0.75rem'}} />Risk Assessor
        </div>
        <div className={styles.title2}>Sign In</div>
        
        {error && <div className={styles.error}>{error}</div>}
        
        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.formGroup}>
            <label htmlFor="email">Email:</label>
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
            <label htmlFor="password">Password:</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className={styles.input}
            />
          </div>
          
          <button 
            type="submit" 
            className={styles.button}
            disabled={loading}
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
        
        <div className={styles.links}>
          {federatedSsoEnabled && (
            <a href="#" onClick={(e) => { e.preventDefault(); setAuthMethod('select'); }}>
              ← Back to sign-in options
            </a>
          )}
          {!federatedSsoEnabled && (
            <Link href="/signup">
              Don&apos;t have an account? Sign up
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
