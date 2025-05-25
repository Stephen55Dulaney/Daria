import React, { useState } from 'react';
import Head from 'next/head';
import {
  AppBar,
  Box,
  Container,
  Tab,
  Tabs,
  ThemeProvider,
  Typography,
  createTheme,
} from '@mui/material';
import { ResearchInsights } from '../components/ResearchInsights';

// Create a custom theme
const theme = createTheme({
  palette: {
    primary: {
      main: '#2196f3',
    },
    secondary: {
      main: '#f50057',
    },
  },
  typography: {
    h1: {
      fontSize: '2.5rem',
      fontWeight: 600,
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 500,
    },
  },
});

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`research-tabpanel-${index}`}
      aria-labelledby={`research-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

export default function ResearchPage() {
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(false);
  const [insights, setInsights] = useState([]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleSearch = async (query: string) => {
    setLoading(true);
    try {
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query }),
      });
      
      if (!response.ok) {
        throw new Error('Search failed');
      }
      
      const data = await response.json();
      setInsights(data.insights);
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <Head>
        <title>Research Insights | UX Research Tool</title>
        <meta name="description" content="Search and analyze UX research insights" />
      </Head>

      <AppBar position="static" color="default">
        <Container maxWidth="lg">
          <Box sx={{ py: 2 }}>
            <Typography variant="h1" component="h1" gutterBottom>
              Research Insights
            </Typography>
            <Tabs
              value={tabValue}
              onChange={handleTabChange}
              indicatorColor="primary"
              textColor="primary"
            >
              <Tab label="Insights" />
              <Tab label="Affinity Diagram" />
              <Tab label="Analytics" />
            </Tabs>
          </Box>
        </Container>
      </AppBar>

      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <TabPanel value={tabValue} index={0}>
          <ResearchInsights
            insights={insights}
            onSearch={handleSearch}
            loading={loading}
          />
        </TabPanel>
        
        <TabPanel value={tabValue} index={1}>
          <Typography variant="h2" gutterBottom>
            Affinity Diagram
          </Typography>
          {/* Add Affinity Diagram component here */}
        </TabPanel>
        
        <TabPanel value={tabValue} index={2}>
          <Typography variant="h2" gutterBottom>
            Analytics
          </Typography>
          {/* Add Analytics component here */}
        </TabPanel>
      </Container>
    </ThemeProvider>
  );
} 