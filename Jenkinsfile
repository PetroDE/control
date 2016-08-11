node {
    stage 'Checkout'
    checkout scm
    stage 'Test'
    sh "make jenkins-test"
    step([$class: 'JUnitResultArchiver', testResults: 'results*.xml'])
}
