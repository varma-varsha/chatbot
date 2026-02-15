import React, { useEffect, useState } from 'react';
import { BookOpen } from 'lucide-react';

const CourseSidebar = () => {
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchUserCourses();
  }, []);

  const fetchUserCourses = async () => {
    try {
      const response = await fetch('/api/get_user_courses');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setCourses(data.courses || []);
    } catch (error) {
      console.error('Error fetching courses:', error);
      setError('Failed to load courses');
    } finally {
      setLoading(false);
    }
  };

  const handleCourseClick = (language) => {
    // Using showPopup from window object
    if (typeof window.showPopup === 'function') {
      window.showPopup(language);
    } else {
      console.error('showPopup function is not defined');
    }
  };

  if (error) {
    return (
      <aside className="fixed right-0 top-0 h-full w-64 bg-white shadow-lg border-l border-gray-200">
        <div className="p-4 text-red-500">
          <p>{error}</p>
          <button
            onClick={fetchUserCourses}
            className="mt-2 text-blue-500 hover:text-blue-600"
          >
            Try Again
          </button>
        </div>
      </aside>
    );
  }

  if (loading) {
    return (
      <aside className="fixed right-0 top-0 h-full w-64 bg-white shadow-lg border-l border-gray-200">
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      </aside>
    );
  }

  return (
    <aside className="fixed right-0 top-0 h-full w-64 bg-white shadow-lg border-l border-gray-200 overflow-y-auto">
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-800">My Courses</h2>
      </div>
      <div className="p-4 space-y-4">
        {courses.length > 0 ? (
          courses.map((course) => (
              <div
                  key={course.language}
                  onClick={() => handleCourseClick(course.language)}
                  className="cursor-pointer group hover:bg-blue-50 rounded-lg p-3 transition-all border-b border-gray-200 last:border-b-0"
              >

                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0">
                    <BookOpen className="h-5 w-5 text-blue-500 group-hover:text-blue-600"/>
                  </div>
                  <div className="flex-1">
                    <h3 className="font-medium text-gray-800">
                      {course.language} Course
                    </h3>
                    <div className="mt-1">
                      <div
                          className="relative w-full h-2 bg-gray-200 rounded"
                          style= "width: {Math.round(course.progress_percentage)}%"
                      >
                        <div
                            className="absolute top-0 left-0 h-full bg-blue-500 rounded"
                        ></div>
                      </div>
                      <p className="text-sm text-gray-500 mt-1">
                         {Math.round(course.progress_percentage)}%Complete
                      </p>
                    </div>
                  </div>
                </div>
              </div>
          ))
        ) : (
            <div className="text-center text-gray-500">
              <p>No courses available</p>
            </div>
        )}
      </div>
    </aside>
  );
};



export default CourseSidebar;