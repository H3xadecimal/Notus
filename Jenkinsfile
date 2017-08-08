pipeline {
    agent {
        docker {
            image 'pandentia/jenkins-discordpy-rewrite'
        }
    }
    stages {
        stage('Test') {
            steps {
                sh 'cloc .'
                sh 'flake8 --show-source --max-line-length 120 .'
                sh 'python -m compileall -x discord.* .'
            }
        }
    }
    post {
        always {
            sh 'rm -rf * | true'
        }
    }
}
