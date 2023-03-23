import {useState, useEffect} from 'react'
import './App.css'
import generateAnswer from './components/GPT3_API.jsx';
import CreateNewEntry from './components/CreateNewEntry.jsx';
import DiaryEntry from "./components/DiaryEntry.jsx";
import {v4 as uuid} from 'uuid';
import RecordVoice from "./components/RecordVoice.jsx";

const App = () => {
    const [prompt, setPrompt] = useState('');
    const [answer, setAnswer] = useState('');
    const [entries, setEntries] = useState([]);

    const handleSubmit = event => {
        event.preventDefault();
        setPrompt(event.target.elements.prompt.value);
    };

    const addEntry = transcript => {
        const entry = {
            id: uuid(),
            text: transcript,
            date: new Date().toLocaleDateString()
        }
        setEntries([...entries, entry]);
    }

    useEffect(() => {
        if (prompt) {
            generateAnswer(prompt).then(completion => setAnswer(completion));
        }
    }, [prompt]);

    return (
        <div>
            <RecordVoice/>
        </div>
    );
};

export default App;

