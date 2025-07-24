import { useRouter } from 'next/router';
import Image from 'next/image';
import logo from '../images/logo-risk.png';
import { useEffect, useState } from 'react';

import { Amplify, Auth } from 'aws-amplify';

interface SidebarProps {
  activePage?: string;
  startCollapsed?: boolean;
}

export default function Sidebar({ activePage, startCollapsed}: SidebarProps) {
  const router = useRouter();
  const [user, setUser] = useState<string | null>(null);
  const [isCollapsed, setIsCollapsed] = useState(startCollapsed);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const currentUser = await Auth.currentAuthenticatedUser();
        console.log( currentUser);
        setUser(currentUser.attributes.email);
      } catch (error) {
        setUser(null);
      }
    };
    fetchUser();
  }, []);

  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '🏠', path: '/' },
    { id: 'risk-assessment', label: 'Risk Assessment', icon: '🛡️', path: '/risk-assessment' },
    // { id: 'demo-page', label: 'Risk Assessment', icon: '🛡️', path: '/demo-page' },
    { id: 'separator'},
    { id: 'projects', label: 'Projects', icon: '📊', path: '/projects' },
    { id: 'new-project', label: 'New Project', icon: '➕', path: '/new-project' },
    { id: 'organization-profiles', label: 'Organization Profiles', icon: '🏢', path: '/organization-profiles' },
    // { id: 'agents', label: 'Agents', icon: '🤖', path: '/agents' },
    { id: 'monitor-agents', label: 'Monitor Agents', icon: '📊', path: '/assessment-flow' },
    { id: 'admin', label: 'Admin', icon: '⚙️', path: '/admin' }
  ];

  const menuItemBackgroundColor = '#ffffff';
  const menuItemTextColor = '#6e6e6eff';
  const menuItemFontSize = '1.1rem';
  const menuItemFontWeight = 'normal';
  
  const menuItemHoverBackgroundColor = '#ddddddff';
  const menuItemHoverTextColor = '#000000ff';
  const menuItemHoverFontSize = '1.1rem';
  const menuItemHoverFontWeight = 'normal';

  const menuItemActiveBackgroundColor = '#d4d4d4ff';
  const menuItemActiveTextColor = '#363636ff';
  const menuItemActiveFontSize = '1.1rem';
  const menuItemActiveFontWeight = 'normal';
  
  return (
    <div style={{
      width: isCollapsed ? '60px' : '250px',
      backgroundColor: '#ffffff',
      borderRight: '2px solid #ff6b35',
      display: 'flex',
      flexDirection: 'column',
      padding: 0,
      transition: 'width 0.3s ease'
    }}>
      <div style={{
        padding: '1rem',
        backgroundColor: '#ffffffff',
        color: '#ff6b35',
        fontWeight: 600,
        fontSize: '1.5rem',
        borderBottom: '1px solid #e55a2b',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center' }} title="Risk Assessor">
          {!isCollapsed && <Image src={logo} alt='logo' width={20} height={20} style={{ marginRight: isCollapsed ? 0 : '0.75rem' }} />}
          {!isCollapsed && 'Risk Assessor'}
        </div>
        <div 
          onClick={() => setIsCollapsed(!isCollapsed)}
          title={isCollapsed ? 'Expand' : 'Collapse'}
          style={{
            cursor: 'pointer',
            fontSize: '1.2rem',
            padding: '0.25rem'
          }}
        >
          ☰
        </div>
      </div>
      
      {menuItems.map(item => (
        item.id == 'separator' ? (
          <div key={item.id} style={{ borderBottom: '1px solid #dfdfdfff', margin: '1rem 0' }}></div>
        ) : (
        <div
          key={item.id}
          style={{
            padding: '1rem',
            border: '0px',
            cursor: 'pointer',
            fontFamily: 'Arial, sans-serif',
            backgroundColor: activePage === item.id ? menuItemActiveBackgroundColor : menuItemBackgroundColor,
            color: activePage === item.id ? menuItemActiveTextColor : menuItemTextColor,
            fontWeight: activePage === item.id ? menuItemActiveFontWeight : menuItemFontWeight,
            fontSize: activePage === item.id ? menuItemActiveFontSize : menuItemFontSize,
            display: 'flex',
            alignItems: 'center',
            justifyContent: isCollapsed ? 'center' : 'flex-start'
          }}
          onClick={() => {
            if (item.id === 'monitor-agents') {
              window.open(item.path, '_blank');
            } else {
              router.push(item.path as string);
            }
          }}
          title={item.label}
          onMouseEnter={(e) => {
            if ( activePage != item.id ){
              e.currentTarget.style.backgroundColor = menuItemHoverBackgroundColor;
              e.currentTarget.style.color = menuItemHoverTextColor;
              e.currentTarget.style.fontSize = menuItemHoverFontSize;
              e.currentTarget.style.fontWeight = menuItemHoverFontWeight;
            }
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = activePage === item.id ? menuItemActiveBackgroundColor : menuItemBackgroundColor;
            e.currentTarget.style.color = activePage === item.id ? menuItemActiveTextColor : menuItemTextColor;
            e.currentTarget.style.fontSize = activePage === item.id ? menuItemActiveFontSize : menuItemFontSize;
            e.currentTarget.style.fontWeight = activePage === item.id ? menuItemActiveFontWeight : menuItemFontWeight;
          }}
        >
          <span style={{ fontSize: '1.2rem', marginRight: isCollapsed ? 0 : '0.75rem' }}>{item.icon}</span>
          {!isCollapsed && <span>{item.label}</span>}
        </div>
        )
      ))}

      <div style={{ 
          position: 'fixed',
          bottom: '1.5rem',
          width: isCollapsed ? '58px' : '248px'
        }}>
        <div style={{ 
          borderBottom: '1px solid #dfdfdfff', 
          margin: '1rem 0' 
        }}></div>

        <div style={{
          padding: '0 1rem',
          border: '0px',
          cursor: 'pointer',
          fontFamily: 'Arial, sans-serif',
          backgroundColor: menuItemBackgroundColor,
          color: menuItemTextColor,
          fontWeight: menuItemFontWeight,
          fontSize: '0.9rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: isCollapsed ? 'center' : 'flex-start',
          marginBottom: '0.5rem'
        }}
        onClick={() => router.push('/downloads')}
        title="Downloads"
        >
          <span style={{ marginRight: isCollapsed ? 0 : '0.5rem' }}>📥</span>
          {!isCollapsed && <span>Downloads</span>}
        </div>

        <div style={{
          padding: '0 1rem',
          border: '0px',
          cursor: 'pointer',
          fontFamily: 'Arial, sans-serif',
          backgroundColor: menuItemBackgroundColor,
          color: menuItemTextColor,
          fontWeight: menuItemFontWeight,
          fontSize: menuItemFontSize,
          display: 'flex',
          alignItems: 'center',
          justifyContent: isCollapsed ? 'center' : 'flex-start'
        }}
        onClick={() => router.push('/login')}
        title="Logout"
        >
          <div style={{ fontSize: '1rem', display: 'flex', alignItems: 'center' }} >
            <span style={{ marginRight: isCollapsed ? 0 : '0.5rem' }}>↩️</span>
            {!isCollapsed && <span>{user}</span>}
          </div>

        </div>
      </div>

    </div>
  );
}
