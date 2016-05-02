node {
    stage 'Checkout'
    checkout scm
    stage 'Test'
    sh "./tests.sh"
    step([$class: 'JUnitResultArchiver', testResults: 'results.xml'])
}
