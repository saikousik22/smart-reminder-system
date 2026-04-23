import React, { useState, useRef, useEffect } from 'react';
import { Mic, Square, Play, Trash2, RotateCcw, Volume2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const AudioRecorder = ({ onRecordingComplete, initialAudioUrl }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState(initialAudioUrl || null);
  const [recordingTime, setRecordingTime] = useState(0);
  
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  // Revoke blob URL when it changes or component unmounts to prevent memory leaks
  useEffect(() => {
    return () => {
      if (audioUrl && audioUrl.startsWith('blob:')) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [audioUrl]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        const url = URL.createObjectURL(blob);
        setAudioBlob(blob);
        setAudioUrl(url);
        
        // Convert blob to file for standard form upload
        const file = new File([blob], 'recording.webm', { type: 'audio/webm' });
        onRecordingComplete(file);
        
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
    } catch (err) {
      console.error("Could not start recording", err);
      alert("Microphone access denied or not available.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      clearInterval(timerRef.current);
    }
  };

  const resetRecording = () => {
    setAudioBlob(null);
    setAudioUrl(null);
    setRecordingTime(0);
    onRecordingComplete(null);
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-2">
        <label className="text-sm font-medium text-slate-300">Voice Message</label>
        {isRecording && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-2 text-rose-500 font-mono text-sm"
          >
            <div className="w-2 h-2 rounded-full bg-rose-500 animate-pulse"></div>
            {formatTime(recordingTime)}
          </motion.div>
        )}
      </div>

      <div className="glass-card rounded-xl p-6 border-dashed border-2 border-white/10 flex flex-col items-center justify-center min-h-[160px]">
        <AnimatePresence mode="wait">
          {!audioUrl && !isRecording ? (
            <motion.div 
              key="start"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="flex flex-col items-center"
            >
              <button
                type="button"
                onClick={startRecording}
                aria-label="Start recording"
                className="w-16 h-16 rounded-full bg-primary-600/20 text-primary-400 flex items-center justify-center hover:bg-primary-600/30 transition-all mb-4 group"
              >
                <Mic className="w-8 h-8 group-hover:scale-110 transition-transform" />
              </button>
              <p className="text-slate-400 text-sm">Click to start recording</p>
            </motion.div>
          ) : isRecording ? (
            <motion.div 
              key="recording"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="flex flex-col items-center"
            >
              <button
                type="button"
                onClick={stopRecording}
                aria-label="Stop recording"
                className="w-16 h-16 rounded-full bg-rose-600/20 text-rose-500 flex items-center justify-center hover:bg-rose-600/30 transition-all mb-4"
              >
                <Square className="w-8 h-8 fill-current" />
              </button>
              <p className="text-rose-400 text-sm font-medium">Recording in progress...</p>
            </motion.div>
          ) : (
            <motion.div 
              key="preview"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="w-full flex flex-col items-center"
            >
              <div className="w-full bg-white/5 rounded-lg p-4 flex items-center gap-4 mb-4 border border-white/10">
                <Volume2 className="text-primary-400 w-5 h-5 flex-shrink-0" />
                <audio src={audioUrl} controls className="h-8 flex-grow" />
              </div>
              <div className="flex gap-4">
                <button
                  type="button"
                  onClick={resetRecording}
                  aria-label="Record again"
                  className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors text-sm"
                >
                  <RotateCcw className="w-4 h-4" />
                  Record Again
                </button>
                <button
                  type="button"
                  onClick={resetRecording}
                  aria-label="Remove recording"
                  className="flex items-center gap-2 text-rose-400 hover:text-rose-300 transition-colors text-sm"
                >
                  <Trash2 className="w-4 h-4" />
                  Remove
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default AudioRecorder;
