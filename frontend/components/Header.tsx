import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { getCurrentUser, signOut } from '../utils/auth';
import styles from '../styles/Header.module.css';

export default function Header() {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [showAdminDropdown, setShowAdminDropdown] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const fetchUser = async () => {
      const { user } = await getCurrentUser();
      setUser(user);
      setLoading(false);
    };

    fetchUser();
  }, []);

  const handleSignOut = async () => {
    await signOut();
    router.push('/login');
  };

  return (
    <header className={styles.header}>
      <div className={styles.logo}>
        <Link href="/">
          <span className={styles.logoIcon}>🔒</span> RiskAgent
        </Link>
      </div>
      
      <nav className={styles.nav}>
        <Link href="/" className={router.pathname === '/' ? styles.active : ''}>
          Home
        </Link>
        <Link href="/projects" className={router.pathname === '/projects' ? styles.active : ''}>
          Projects
        </Link>
        <Link href="/risks" className={router.pathname === '/risks' ? styles.active : ''}>
          Risks
        </Link>
        <Link href="/assessment-flow" className={router.pathname === '/assessment-flow' ? styles.active : ''}>
          Agents
        </Link>
        <div 
          className={styles.dropdown}
          onMouseEnter={() => setShowAdminDropdown(true)}
          onMouseLeave={() => setShowAdminDropdown(false)}
        >
          <Link href="/admin" className={router.pathname === '/admin' ? styles.active : ''}>
            Administration ▼
          </Link>
          {showAdminDropdown && (
            <div className={styles.dropdownMenu}>
              <Link href="/admin" className={styles.dropdownItem}>
                Security Controls Dashboard
              </Link>
            </div>
          )}
        </div>
      </nav>
      
      <div className={styles.auth}>
        {!loading && (
          user ? (
            <>
              <span className={styles.email}>{user.attributes?.email}</span>
              <button onClick={handleSignOut} className={styles.signOutButton}>
                Sign Out
              </button>
            </>
          ) : (
            <Link href="/login" className={styles.signInButton}>
              Sign In
            </Link>
          )
        )}
      </div>
    </header>
  );
}